// @ts-check
/** @typedef {{id:number,email:string,name:string,role:string,department:string,fingerprint:string,active:number}} User */
/** @typedef {{id:number,code:string,title:string,year:string,semester:string,department:string,teacher_id:number,co_teacher_id:number|null,submitted_assessments:string[],assessment_statuses:Record<string,string>,uis_document_id:string,uis_component_document_id:string,teaching_schedule:string,teaching_room:string,teaching_weeks:string}} Course */
/** @typedef {{signer_name?:string,field:string,signer_emails?:string[],fingerprint?:string,trust_verified?:boolean,revocation_verified?:boolean,validation_policy?:string}} Signature */
/** @typedef {{signatures:Signature[],id:number,course_id:number,version:number,status:string,reason:string,code:string,title:string,year:string,semester:string,department:string,teacher_name:string,updated_at:string,assessment_type:string,document_label:string}} Submission */
/** @type {{user:User|null,csrf:string,deadline:string|null,courses:Course[],items:Submission[],page:number,pages:number,total:number,view:string}} */
const state = {user:null,csrf:'',deadline:null,courses:[],items:[],page:1,pages:1,total:0,view:'dashboard'};
/** @type {Record<string,string>} */
const roles = {teacher:'Giảng viên',head:'Trưởng khoa',training:'Đào tạo & BĐCL',admin:'Quản trị viên'};
/** @type {Record<string,string>} */
const statuses = {submitted:'Chờ trưởng khoa',head_signed:'Chờ Đào tạo',rejected:'Đã trả lại',archived:'Đã lưu trữ'};
/** @type {Record<string,string>} */
const teacherStatuses = {submitted:'Chờ Trưởng khoa duyệt',head_signed:'Chờ Đào tạo duyệt',archived:'Hoàn thành'};
/** @param {string} status */
function statusLabel(status){
  if(state.user?.role==='teacher')return teacherStatuses[status]||statuses[status];
  if(state.user?.role==='training'){
    if(status==='head_signed')return 'Đang chờ P.ĐT duyệt';
    if(status==='archived')return 'Đã lưu';
  }
  return status==='submitted'&&state.user?.role==='head'?'Chưa ký':statuses[status];
}
/** @type {Record<string,string>} */
const assessmentTypes = {final:'Bảng điểm cuối kỳ',component:'Bảng điểm thành phần',other:'Bảng điểm khác'};
let uploadRefreshGeneration=0;
let listRefreshGeneration=0;
/** @param {string} title */
function guidanceCourse(title){return /(?:^|[^\p{L}\p{N}_])(?:đồ án|đề án|thực tập|kiến tập)(?=$|[^\p{L}\p{N}_])/u.test(title.normalize('NFC').toLocaleLowerCase('vi').replace(/\s+/g,' ').trim());}
/** @param {string} title @param {string} kind */
function uploadLabel(title,kind){return guidanceCourse(title)?(kind==='component'?'Nộp điểm hướng dẫn':'Nộp điểm Hội đồng'):(kind==='component'?'Nộp điểm thành phần':'Nộp điểm Cuối kỳ');}
const app = document.querySelector('#app');
if (!(app instanceof HTMLElement)) throw new Error('Missing app root');
const root = app;
/** @param {unknown} text */
function esc(text) { return String(text??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]||c)); }
/** @param {Signature[]} signatures */
function signerInfo(signatures){
  return signatures.length?`<ul>${signatures.map(signature=>`<li><strong>${esc(signature.signer_name||'Chưa lưu tên trên chứng thư')}</strong>${signature.signer_emails?.length?` · ${esc(signature.signer_emails.join(', '))}`:''}<small>${signature.trust_verified&&signature.revocation_verified?'Đã xác minh CA và thu hồi chứng thư':signature.validation_policy==='local'?'Đã kiểm tra mật mã và tính toàn vẹn · CA/thu hồi chưa xác minh':'Kết quả kiểm tra đã lưu trước đây'}</small>${signature.fingerprint?`<small>Fingerprint SHA-256: <span style="overflow-wrap:anywhere">${esc(signature.fingerprint)}</span></small>`:''}</li>`).join('')}</ul>`:'<p>Chưa có thông tin người ký được lưu.</p>';
}
/** @param {string} id @returns {HTMLInputElement} */
function input(id) {const e=document.getElementById(id);if(!(e instanceof HTMLInputElement))throw new Error(id);return e;}
/** @param {string} id @returns {HTMLFormElement} */
function form(id) {const e=document.getElementById(id);if(!(e instanceof HTMLFormElement))throw new Error(id);return e;}
/** @param {string} id @returns {HTMLSelectElement} */
function select(id) {const e=document.getElementById(id);if(!(e instanceof HTMLSelectElement))throw new Error(id);return e;}
/** @param {string} text @param {boolean} error */
function message(text,error=false) { const e=document.getElementById('message');if(e){e.textContent=text;e.className=error?'toast error':'toast';e.hidden=false;setTimeout(()=>{e.hidden=true;},8000);} }
/** @param {string} url @param {RequestInit} options @returns {Promise<any>} */
async function api(url,options={}) {
  const mutation=!['GET','HEAD','OPTIONS'].includes((options.method||'GET').toUpperCase())&&url!=='/api/login';
  const userId=state.user?.id;
  /** @returns {Promise<void>} */
  async function syncSession(){
    const session=await api('/api/me');
    if(session.user.id!==userId){
      state.user=session.user;state.csrf=session.csrf;state.deadline=session.deadline;
      await dashboard();
      throw new Error('Phiên đăng nhập đã đổi tài khoản hoặc vai trò. Màn hình đã được cập nhật; hãy kiểm tra lại trước khi thao tác.');
    }
    state.csrf=session.csrf;
  }
  if(mutation)await syncSession();
  const headers=new Headers(options.headers);headers.set('X-CSRF-Token',state.csrf);
  if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
  let r=await fetch(url,{...options,headers});let data=await r.json();
  // CSRF rejection occurs before the handler; only this failure is safe to retry.
  if(mutation&&r.status===403&&data.detail==='CSRF token không hợp lệ. Tải lại trang rồi thử lại.'){
    await syncSession();headers.set('X-CSRF-Token',state.csrf);
    r=await fetch(url,{...options,headers});data=await r.json();
  }
  if(!r.ok){if(r.status===401 && state.user){state.user=null;state.csrf='';loginView();}throw new Error(typeof data.detail==='string'?data.detail:'Dữ liệu chưa hợp lệ. Kiểm tra các trường và thử lại.');}
  return data;
}
/** @param {() => Promise<void>} action @param {HTMLElement|null} element */
async function busy(action,element=null){if(element instanceof HTMLButtonElement)element.disabled=true;try{await action();}catch(e){message(e instanceof Error?e.message:'Không kết nối được máy chủ.',true);}finally{if(element instanceof HTMLButtonElement)element.disabled=false;}}

function loginView(){
  root.innerHTML=`<main class="login"><section class="intro"><a class="brand" href="/">VKU<span>E-GRADEBOOK</span></a><div class="eyebrow">BẢNG ĐIỂM ĐIỆN TỬ</div><h1>Ký số bên ngoài.<br>Nộp và quản lý<br>tại một nơi.</h1><p>Quy trình xuyên suốt từ giảng viên, trưởng khoa đến Phòng Đào tạo và Bảo đảm chất lượng.</p><div class="flow"><span>01 · Giảng viên</span><b>→</b><span>02 · Trưởng khoa</span><b>→</b><span>03 · Lưu trữ</span></div></section><section class="login-panel"><div class="eyebrow">CỔNG NỘP BẢNG ĐIỂM</div><h2>Đăng nhập</h2><p class="muted">Sử dụng tài khoản email VKU đã được cấp quyền.</p><form id="login-form"><label>Vai trò đăng nhập<select id="login-role" name="role" required><option value="teacher">GV · Giảng viên</option><option value="head">TK · Trưởng khoa</option><option value="training">ĐT · Phòng ĐT & BĐCL</option><option value="admin">Admin · Quản trị viên</option></select></label><p class="muted">Một email có thể có nhiều vai trò. Chọn vai trò đã được cấp để đăng nhập.</p><label>Email trường<input id="email" name="email" type="email" autocomplete="username" placeholder="ten@vku.udn.vn" required></label><label>Mật khẩu<input id="password" name="password" type="password" autocomplete="current-password" required></label><button class="primary" type="submit">Đăng nhập <span>→</span></button></form><p class="help">Chưa có tài khoản hoặc quên mật khẩu? Liên hệ quản trị viên của trường để được cấp lại.</p><div class="note">PDF gốc · Xác thực chữ ký số · Lịch sử xử lý</div></section></main>`;
  form('login-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{const data=await api('/api/login',{method:'POST',body:JSON.stringify({email:input('email').value,password:input('password').value,role:select('login-role').value})});state.user=data.user;state.csrf=data.csrf;await dashboard();},form('login-form').querySelector('button'));};
}

function shell(){
  const u=state.user;if(!u)return;
  root.innerHTML=`<div class="layout"><aside class="sidebar"><a class="brand" href="/">VKU<span>E-GRADEBOOK</span></a><div class="side-label">KHÔNG GIAN LÀM VIỆC</div><button class="nav ${state.view==='dashboard'?'selected':''}" data-action="dashboard">▦ &nbsp; Bảng điểm</button>${u.role==='admin'?`<button class="nav ${state.view==='admin'?'selected':''}" data-action="admin">⚙ &nbsp; Quản trị hệ thống</button>`:''}<div class="sidebar-bottom"><span class="avatar">${esc(u.name.slice(0,1))}</span><strong>${esc(u.name)}</strong><small>${esc(roles[u.role])}<br>${esc(u.department)}</small><button class="logout" data-action="logout">Đăng xuất</button></div></aside><main class="workspace"><header><span>VKU / ${esc(roles[u.role])}</span><span class="secure">● &nbsp; Quản lý bảng điểm ký số</span></header><div id="content"></div><footer>VKU E-Gradebook · Giữ nguyên tài liệu, lưu dấu mọi bước xử lý.</footer></main></div><dialog id="detail-dialog"><div id="detail"></div></dialog>`;
  root.onclick=e=>{const target=e.target instanceof Element?e.target.closest('[data-action]'):null;if(!(target instanceof HTMLElement))return;const action=target.dataset.action;void busy(async()=>{if(action==='logout'){await api('/api/logout',{method:'POST'});state.user=null;loginView();}if(action==='dashboard'){state.view='dashboard';await dashboard();}if(action==='admin'){state.view='admin';await adminView();}if(action==='detail')await detail(Number(target.dataset.id));if(action==='close'){const d=document.getElementById('detail-dialog');if(d instanceof HTMLDialogElement)d.close();}},target);};
}

/** @param {string} html */
function content(html){const e=document.getElementById('content');if(e)e.innerHTML=html;}
async function dashboard(){
  const me=await api('/api/me');state.deadline=me.deadline;
  state.courses=await api('/api/courses');state.page=1;shell();
  const u=state.user;if(!u)return;
  const expired=state.deadline&&new Date(state.deadline)<new Date();
  content(`<section class="page-heading"><div class="eyebrow">QUY TRÌNH BẢNG ĐIỂM</div><h1>${u.role==='teacher'?'Bảng điểm của tôi':u.role==='head'?'Duyệt bảng điểm của khoa':'Kho bảng điểm điện tử'}</h1><p>${u.role==='teacher'?'Nộp PDF đã ký số và theo dõi từng bước xử lý.':u.role==='head'?'Kiểm tra, tải PDF để ký số và chuyển đến Phòng Đào tạo.':'Tiếp nhận, xác minh và tra cứu bảng điểm theo học kỳ.'}</p></section><div class="deadline ${expired?'expired':''}">${state.deadline?`${expired?'Đã hết hạn · chỉ xem đối với GV và TK':'Thời hạn nộp'}: ${esc(new Date(state.deadline).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}))}`:'Chưa đặt thời hạn nộp. Quản trị viên cần cấu hình trước đợt nộp.'}</div>${u.role==='teacher'?`<section class="upload-card"><div><span class="step">01</span><h2>Gửi bảng điểm đã ký</h2><p>Xuất từ UIS, ký bằng VGCA Sign Tool rồi nộp PDF gốc. Tối đa 20 MB.</p></div><form id="upload-form"><label>Lớp học phần<select name="course_id" required><option value="">Chọn lớp học phần</option>${state.courses.map(c=>`<option value="${c.id}">${esc(c.code+' · '+c.title+' · HK'+c.semester+' '+c.year)}</option>`).join('')}</select></label><a id="export-link" class="text-link" hidden>Tải PDF xuất từ UIS ↗</a><label>PDF đã có chữ ký giảng viên<input type="file" name="file" accept="application/pdf,.pdf" required ${expired?'disabled':''}></label><button class="primary" type="submit" ${expired?'disabled':''}>Gửi trưởng khoa →</button></form></section>`:''}<section class="records"><div class="section-heading"><h2>Danh sách bảng điểm</h2><span id="total" class="muted"></span></div><form id="filters" class="filters"><label class="search">Tìm kiếm<input name="q" placeholder="Mã lớp, môn học, giảng viên…"></label><label>Năm học<input name="year" placeholder="2025-2026"></label><label>Học kỳ<select name="semester"><option value="">Tất cả</option><option>1</option><option>2</option><option>3</option></select></label><label>Khoa<input name="department" placeholder="Tất cả khoa"></label><label>Trạng thái<select name="status"><option value="">Tất cả</option>${Object.keys(statuses).map(k=>`<option value="${k}">${esc(statusLabel(k))}</option>`).join('')}</select></label><button type="submit" class="secondary">Lọc</button></form><div id="table"></div><div class="pagination"><button id="prev" class="secondary">← Trước</button><span id="page"></span><button id="next" class="secondary">Sau →</button></div></section>`);
  const departmentFilter=form('filters').querySelector('[name=department]');
  if(u.role==='training'){
    const years=[...new Set(state.courses.map(c=>c.year))].sort().reverse();
    document.querySelector('#content .records')?.insertAdjacentHTML('beforebegin',`<section class="records" id="department-statistics" aria-live="polite"><h2>Thống kê nộp bảng điểm theo Khoa</h2><div class="filters"><label>Năm học<select id="statistics-year" aria-label="Năm học thống kê"><option value="">Tất cả năm học</option>${years.map(year=>`<option value="${esc(year)}">${esc(year)}</option>`).join('')}</select></label><label>Học kỳ<select id="statistics-semester" aria-label="Học kỳ thống kê"><option value="">Tất cả học kỳ</option><option value="1">Học kỳ 1</option><option value="2">Học kỳ 2</option><option value="3">Học kỳ hè</option></select></label></div><p class="muted">Chọn năm học và học kỳ để thống kê; khoa theo bộ lọc danh sách bên dưới. Mỗi lớp tính một lần khi có ít nhất một hồ sơ đã nộp, kể cả hồ sơ bị trả lại; không yêu cầu đã nộp đủ hai loại. Tổng là số lớp học phần trong danh mục, bao gồm lớp chưa nộp.</p><div id="department-statistics-table"></div></section>`);
    const changePeriod=()=>{
      const year=form('filters').querySelector('[name=year]'),semester=form('filters').querySelector('[name=semester]');
      if(year instanceof HTMLInputElement)year.value=select('statistics-year').value;
      if(semester instanceof HTMLSelectElement)semester.value=select('statistics-semester').value;
      state.page=1;void busy(loadList);
    };
    select('statistics-year').onchange=changePeriod;select('statistics-semester').onchange=changePeriod;
  }
  if(departmentFilter instanceof HTMLInputElement){
    const departments=[...new Set(state.courses.map(c=>c.department))].sort((a,b)=>a.localeCompare(b,'vi'));
    const units=u.role==='training'?(await api('/api/statistics/departments')).items.map(/** @param {{department:string,department_name:string}} unit */unit=>({code:unit.department,name:unit.department_name})):departments.map(code=>({code,name:code}));
    departmentFilter.outerHTML=`<select name="department" aria-label="Khoa"><option value="">Tất cả khoa</option>${units.map(/** @param {{code:string,name:string}} unit */unit=>`<option value="${esc(unit.code)}">${esc(unit.name)}</option>`).join('')}</select>`;
  }
  if(me.signature_policy==='local'){
    document.querySelector('#content .deadline')?.insertAdjacentHTML('afterend','<p class="note">Chế độ local: kiểm tra chữ ký mật mã, nội dung PDF và người ký. Chưa xác minh CA và tình trạng thu hồi chứng thư.</p>');
  }
  form('filters').querySelector('button')?.insertAdjacentHTML('beforebegin',`<label>Loại bảng điểm<select name="assessment_type"><option value="">Tất cả</option>${Object.entries(assessmentTypes).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></label>`);
  form('filters').onsubmit=e=>{e.preventDefault();state.page=1;void busy(loadList);};
  const prev=document.getElementById('prev'),next=document.getElementById('next');
  if(prev)prev.onclick=()=>{state.page--;void busy(loadList);};if(next)next.onclick=()=>{state.page++;void busy(loadList);};
  if(u.role==='teacher'){
    const f=form('upload-form');
    document.querySelector('.upload-card')?.insertAdjacentHTML('beforebegin',`<section class="records"><h2>Các lớp học phần tôi dạy</h2><div class="filters"><label>Năm học giảng dạy<select id="teaching-year">${[...new Set(state.courses.map(c=>c.year))].sort().reverse().map(y=>`<option>${esc(y)}</option>`).join('')}</select></label><label>Học kỳ giảng dạy<select id="teaching-semester"><option value="1">Học kỳ 1</option><option value="2">Học kỳ 2</option><option value="3">Học kỳ hè</option></select></label></div><div id="teaching-courses"></div></section>`);
    const latest=[...state.courses].sort((a,b)=>b.year.localeCompare(a.year)||Number(b.semester)-Number(a.semester))[0];
    if(latest){select('teaching-year').value=latest.year;select('teaching-semester').value=latest.semester;}
    select('teaching-year').onchange=renderTeachingCourses;select('teaching-semester').onchange=renderTeachingCourses;renderTeachingCourses();
    document.querySelector('.upload-card')?.insertAdjacentHTML('afterend','<section id="submission-receipt" class="note" aria-live="polite" hidden></section>');
    f.insertAdjacentHTML('afterbegin',`<select id="assessment-type" name="assessment_type" hidden>${Object.entries(assessmentTypes).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select><input type="hidden" id="document-label" name="document_label"><select id="upload-target" name="submission_id" hidden><option value="0">Nộp bảng điểm mới</option></select>`);
    f.onchange=e=>{const id=new FormData(f).get('course_id');const a=document.getElementById('export-link');if(a instanceof HTMLAnchorElement){a.hidden=!id;a.href=`/api/courses/${id}/export`;}if(e.target instanceof HTMLSelectElement){if(e.target.name==='course_id'||e.target.name==='assessment_type')void busy(async()=>{await refreshResubmissions();});if(e.target.id==='upload-target')input('document-label').disabled=e.target.value!=='0';}};
    f.onsubmit=e=>{e.preventDefault();void busy(async()=>{const data=new FormData(f);const target=select('upload-target');data.set('version',target.value==='0'?'0':target.selectedOptions[0].dataset.version||'0');const sent=await api('/api/submissions',{method:'POST',body:data});f.reset();input('document-label').disabled=false;await refreshResubmissions();const link=document.getElementById('export-link');if(link)link.hidden=true;message('Đã gửi bảng điểm để trưởng khoa xử lý.');await loadList();const verification=await api(`/api/submissions/${sent.id}/verification`);const receipt=document.getElementById('submission-receipt');if(receipt){receipt.hidden=false;receipt.innerHTML=`<strong>Đã gửi trưởng khoa · Hồ sơ #${sent.id}</strong><p>Người ký trên PDF</p>${signerInfo(verification.signatures)}`;}},f.querySelector('button'));};
  }
  await loadList();
}

function renderTeachingCourses(){
  const host=document.getElementById('teaching-courses');if(!host)return;
  const year=select('teaching-year').value,semester=select('teaching-semester').value;
  const expired=!!state.deadline&&new Date(state.deadline)<new Date();
  const courses=state.courses.filter(c=>c.year===year&&c.semester===semester);
  /** @param {Course} c @param {string} kind */
  const uploadButton=(c,kind)=>{
    const status=c.assessment_statuses?.[kind],sent=(c.submitted_assessments||[]).includes(kind);
    const complete=status==='archived',label=uploadLabel(c.title,kind);
    return `<div class="course-upload-option" data-assessment-status="${esc(kind)}">${complete?`<small>${esc(label.replace(/^Nộp /,''))}</small>`:`<button type="button" class="${kind==='component'?'secondary':'primary'} course-upload" data-course="${c.id}" data-assessment="${kind}" data-resubmit="${status==='rejected'}" ${expired||(sent&&status!=='rejected')?'disabled':''} ${status?`title="${esc(statusLabel(status))}"`:''}>${esc(label)}</button>`}${status?`<small class="assessment-status badge ${esc(status)}" role="status">${esc(statusLabel(status))}</small>`:''}</div>`;
  };
  host.innerHTML=courses.length?courses.map(c=>`<article class="teaching-course"><div><h3>${esc(c.title)}</h3><small>${esc(c.code)} · HK ${esc(c.semester)} · ${esc(c.year)}</small>${c.teaching_schedule?`<small>${esc(c.teaching_schedule)} · Phòng ${esc(c.teaching_room||'Chưa có')} · Tuần ${esc(c.teaching_weeks||'Chưa có')}</small>`:''}${guidanceCourse(c.title)?'':'<small>Cuối kỳ: 2 chữ ký GV khác nhau + 1 chữ ký trưởng khoa. GV ký thứ hai không cần dạy lớp này.</small>'}</div><div class="course-upload-actions">${uploadButton(c,'component')}${uploadButton(c,'final')}</div></article>`).join(''):'<p class="muted">Chưa có lớp học phần được phân công trong học kỳ này.</p>';
  for(const button of host.querySelectorAll('.course-upload'))if(button instanceof HTMLButtonElement)button.onclick=()=>{void busy(async()=>{
    const f=form('upload-form');f.reset();input('document-label').disabled=false;
    const course=f.querySelector('[name=course_id]');if(!(course instanceof HTMLSelectElement))return;
    course.value=button.dataset.course||'';select('assessment-type').value=button.dataset.assessment||'final';
    const rejected=await refreshResubmissions();
    if(button.dataset.resubmit==='true'){
      if(!rejected.length){await loadList();throw new Error('Hồ sơ không còn ở trạng thái bị trả. Danh sách đã được cập nhật.');}
      selectResubmission(rejected[0]);
    }
    const link=document.getElementById('export-link');if(link instanceof HTMLAnchorElement){link.hidden=false;link.href=`/api/courses/${course.value}/export`;}
    f.scrollIntoView({behavior:'smooth',block:'center'});const file=f.querySelector('input[type=file]');if(file instanceof HTMLInputElement)file.focus();
  },button);};
}

/** @returns {Promise<Submission[]>} */
async function refreshResubmissions(){
  const generation=++uploadRefreshGeneration;
  const f=form('upload-form'),data=new FormData(f),cid=Number(data.get('course_id'));
  const target=select('upload-target');target.innerHTML='<option value="0">Nộp bảng điểm mới</option>';input('document-label').disabled=false;
  if(!cid)return [];
  const query=new URLSearchParams({course_id:String(cid),assessment_type:String(data.get('assessment_type')),status:'rejected'});
  const result=await api('/api/submissions?'+query);
  if(generation!==uploadRefreshGeneration)return [];
  for(const row of /** @type {Submission[]} */(result.items))target.insertAdjacentHTML('beforeend',`<option value="${row.id}" data-version="${row.version}">Nộp lại #${row.id} · ${esc(row.document_label||assessmentTypes[row.assessment_type])} · phiên bản ${row.version}</option>`);
  return result.items;
}

/** @param {Submission} row */
function selectResubmission(row){
  const target=select('upload-target');
  if(!Array.from(target.options).some(option=>option.value===String(row.id)))target.add(new Option(`Nộp lại #${row.id}`,String(row.id)));
  target.value=String(row.id);target.selectedOptions[0].dataset.version=String(row.version);
  input('document-label').value=row.document_label;input('document-label').disabled=true;
}

/** @param {Submission} row */
async function prepareResubmission(row){
  const f=form('upload-form'),course=f.querySelector('[name=course_id]');if(!(course instanceof HTMLSelectElement))return;
  course.value=String(row.course_id);select('assessment-type').value=row.assessment_type;
  await refreshResubmissions();selectResubmission(row);
  f.scrollIntoView({behavior:'smooth',block:'center'});const file=f.querySelector('input[type=file]');if(file instanceof HTMLInputElement)file.focus();
}

async function loadList(){
  const generation=++listRefreshGeneration;
  const params=new URLSearchParams();for(const [k,v] of new FormData(form('filters'))){if(typeof v==='string'&&v)params.set(k,v);}params.set('page',String(state.page));
  const statisticsParams=new URLSearchParams();for(const key of ['year','semester','department'])if(params.get(key))statisticsParams.set(key,params.get(key)||'');
  if(state.user?.role==='training'){
    const year=select('statistics-year'),value=params.get('year')||'';
    if(value&&!Array.from(year.options).some(option=>option.value===value))year.add(new Option(value,value));
    year.value=value;select('statistics-semester').value=params.get('semester')||'';
  }
  const [data,courses,statistics]=await Promise.all([api('/api/submissions?'+params),state.user?.role==='teacher'?api('/api/courses'):Promise.resolve(null),state.user?.role==='training'?api('/api/statistics/departments?'+statisticsParams):Promise.resolve(null)]);
  if(generation!==listRefreshGeneration)return;
  const statisticsHost=document.getElementById('department-statistics-table');
  if(statistics&&statisticsHost){
    statisticsHost.innerHTML=statistics.items.length?`<div class="table-wrap"><table><thead><tr><th>Tên Khoa</th><th>Lớp đã nộp bảng điểm / Tổng số lớp học phần</th><th>Chi tiết</th></tr></thead><tbody>${statistics.items.map(/** @param {{department:string,department_name:string,submitted_courses:number,total_courses:number}} row */row=>`<tr><td>${esc(row.department_name||row.department)} <small>${esc(row.department)}</small></td><td>${row.submitted_courses} / ${row.total_courses}</td><td><button type="button" class="secondary department-detail" data-department="${esc(row.department)}" aria-label="Chi tiết ${esc(row.department_name||row.department)}">Chi tiết</button></td></tr>`).join('')}</tbody><tfoot><tr><th>Tổng cộng</th><th>${statistics.submitted_courses} / ${statistics.total_courses}</th><th></th></tr></tfoot></table></div>`:'<p>Chưa có lớp học phần phù hợp để thống kê.</p>';
    for(const button of statisticsHost.querySelectorAll('.department-detail'))if(button instanceof HTMLButtonElement)button.onclick=()=>{void busy(()=>showDepartmentDetails(button.dataset.department||'',statisticsParams),button);};
  }
  if(courses){state.courses=courses;renderTeachingCourses();}
  state.items=data.items;state.total=data.total;state.pages=data.pages;
  const table=document.getElementById('table');if(!table)return;
  table.innerHTML=state.items.length?`<div class="table-wrap"><table><thead><tr><th>Lớp học phần</th><th>Giảng viên / Khoa</th><th>Học kỳ</th><th>Trạng thái</th><th></th></tr></thead><tbody>${state.items.map(s=>`<tr><td><strong>${esc(s.title)}</strong><small>${esc(s.code)} · Phiên bản ${s.version}</small></td><td>${esc(s.teacher_name)}<small>${esc(s.department)}</small></td><td>HK ${esc(s.semester)}<small>${esc(s.year)}</small></td><td><span class="badge ${esc(s.status)}">${esc(statusLabel(s.status))}</span>${s.reason?`<small class="reason">${esc(s.reason)}</small>`:''}</td><td><button class="text-link" data-action="detail" data-id="${s.id}">Mở hồ sơ →</button></td></tr>`).join('')}</tbody></table></div>`:`<div class="empty"><span>▤</span><h3>Chưa có bảng điểm</h3><p>${state.courses.length?'Hồ sơ phù hợp sẽ xuất hiện tại đây sau khi nộp.':'Chưa có lớp được cấu hình. Liên hệ quản trị viên để đồng bộ danh mục UIS.'}</p></div>`;
  for(const [index,tr] of Array.from(table.querySelectorAll('tbody tr')).entries()){
    const row=state.items[index];tr.querySelector('td')?.insertAdjacentHTML('beforeend',`<small><strong>${esc(assessmentTypes[row.assessment_type])}</strong>${row.document_label?' · '+esc(row.document_label):''} · Hồ sơ #${row.id}</small>`);
    if(state.user?.role==='training'){
      if(index===0)table.querySelector('thead th:last-child')?.insertAdjacentHTML('beforebegin','<th>So Khớp</th>');
      tr.lastElementChild?.insertAdjacentHTML('beforebegin','<td><button type="button" class="secondary compare-grades">So Khớp</button></td>');
      const compareButton=tr.querySelector('.compare-grades');
      if(compareButton instanceof HTMLButtonElement)compareButton.onclick=()=>{void busy(()=>showComparison(row),compareButton);};
    }
    tr.children[1]?.insertAdjacentHTML('beforeend',`<small class="signer-summary">Người ký PDF: ${row.signatures.length?row.signatures.map(signature=>esc(signature.signer_name||'Chưa lưu tên trên chứng thư')+(signature.signer_emails?.length?' · '+esc(signature.signer_emails.join(', ')): '')).join('<br>'):'Chưa có thông tin người ký được lưu'}</small>`);
    if(state.user?.role==='training'&&(row.status==='head_signed'||row.status==='archived')){
      const td=tr.children[3];
      td?.insertAdjacentHTML(row.status==='archived'?'afterbegin':'beforeend',`${row.status==='archived'?'':'<br>'}<button type="button" class="secondary approve" ${row.status==='archived'?'disabled':''}>Duyệt</button>${row.status==='archived'?'<br>':''}`);
      const button=td?.querySelector('.approve');
      if(button instanceof HTMLButtonElement)button.onclick=()=>{void busy(async()=>{
        await api(`/api/submissions/${row.id}/archive`,{method:'POST',body:JSON.stringify({version:row.version})});
        message('Đã duyệt và lưu trữ bảng điểm.');await loadList();
      },button);};
    }
    if(state.user?.role==='teacher'&&row.status==='rejected'){
      const td=tr.lastElementChild;td?.insertAdjacentHTML('beforeend',`<br><button class="text-link resubmit">Nộp lại #${row.id}</button>`);
      const button=td?.querySelector('.resubmit');if(button instanceof HTMLButtonElement)button.onclick=()=>{void busy(()=>prepareResubmission(row),button);};
    }
  }
  const total=document.getElementById('total'),page=document.getElementById('page');if(total)total.textContent=`${data.total} hồ sơ`;if(page)page.textContent=`Trang ${state.page}/${state.pages}`;
  const prev=document.getElementById('prev'),next=document.getElementById('next');if(prev instanceof HTMLButtonElement)prev.disabled=state.page<=1;if(next instanceof HTMLButtonElement)next.disabled=state.page>=state.pages;
}

/** @param {string} department @param {URLSearchParams} filters */
async function showDepartmentDetails(department,filters){
  const params=new URLSearchParams();for(const key of ['year','semester'])if(filters.get(key))params.set(key,filters.get(key)||'');
  const info=await api(`/api/statistics/departments/${encodeURIComponent(department)}/details?${params}`);
  const dialog=document.getElementById('detail-dialog'),host=document.getElementById('detail');
  if(!(dialog instanceof HTMLDialogElement)||!host)return;
  host.innerHTML=`<div class="modal-header"><div><h2>Chi tiết ${esc(info.department_name)}</h2><p>${esc(info.year||'Tất cả năm học')} · ${info.semester?'Học kỳ '+esc(info.semester):'Tất cả học kỳ'}</p></div><button type="button" class="secondary" data-action="close" aria-label="Đóng chi tiết khoa">✕</button></div><p>${info.teachers.length} giảng viên · ${info.submitted_courses} / ${info.total_courses} lớp đã nộp bảng điểm. Mỗi lớp tính một lần, kể cả hồ sơ bị trả lại.</p><label>Tìm giảng viên hoặc lớp<input id="department-detail-search" placeholder="Họ tên, email, tên lớp hoặc mã lớp"></label><div id="department-detail-results"></div>`;
  /** @typedef {{id:number,code:string,title:string,year:string,semester:string,submitted:number}} DetailCourse */
  /** @typedef {{id:number,name:string,email:string,total_courses:number,submitted_courses:number,courses:DetailCourse[]}} DetailTeacher */
  const teachers=/** @type {DetailTeacher[]} */(info.teachers);
  const results=document.getElementById('department-detail-results');
  const draw=()=>{
    if(!results)return;
    const query=input('department-detail-search').value.trim().toLocaleLowerCase('vi');
    const matches=teachers.map(t=>({...t,visibleCourses:(t.name+' '+t.email).toLocaleLowerCase('vi').includes(query)?t.courses:t.courses.filter(c=>(c.title+' '+c.code).toLocaleLowerCase('vi').includes(query))})).filter(t=>t.visibleCourses.length);
    results.innerHTML=matches.length?`<div class="table-wrap"><table><thead><tr><th>Giảng viên</th><th>Email</th><th>Đã nộp / Tổng lớp</th></tr></thead><tbody>${matches.map(t=>`<tr><td>${esc(t.name)}</td><td>${esc(t.email)}</td><td>${t.submitted_courses} / ${t.total_courses}</td></tr><tr><td colspan="3"><details ${query?'open':''}><summary>Danh sách lớp (${t.visibleCourses.length}${query?' phù hợp':''})</summary><table><thead><tr><th>Lớp học phần</th><th>Học kỳ / Năm học</th><th>Nộp bảng điểm</th></tr></thead><tbody>${t.visibleCourses.map(c=>`<tr><td>${esc(c.title)}<small>${esc(c.code)}</small></td><td>HK ${esc(c.semester)}<small>${esc(c.year)}</small></td><td>${c.submitted?'Đã nộp':'Chưa nộp'}</td></tr>`).join('')}</tbody></table></details></td></tr>`).join('')}</tbody></table></div>`:`<p>${teachers.length?'Không tìm thấy giảng viên hoặc lớp phù hợp.':'Khoa chưa có lớp học phần trong năm học/học kỳ đã chọn.'}</p>`;
  };
  input('department-detail-search').oninput=draw;draw();dialog.showModal();
}

/** @param {Submission} row */
async function showComparison(row){
  const info=await api(`/api/submissions/${row.id}/comparison`);
  const dialog=document.getElementById('detail-dialog'),host=document.getElementById('detail');
  if(!(dialog instanceof HTMLDialogElement)||!host)return;
  host.innerHTML=`<div class="modal-header"><div><h2>So Khớp điểm</h2><p>${esc(row.title)} · HK ${esc(row.semester)} · ${esc(row.year)}</p></div><button class="secondary" data-action="close" aria-label="Đóng so khớp">✕</button></div><p class="note">Đối chiếu với PDF xuất từ daotao do bạn chọn. PDF có ${info.student_count} sinh viên · phiên bản PDF ${info.pdf_version}.</p><form id="comparison-form"><label>PDF bảng điểm xuất từ daotao<input id="comparison-file" type="file" name="file" accept=".pdf,application/pdf" required></label><div id="comparison-mapping"></div><label class="checkbox"><input type="checkbox" required> Tôi xác nhận file nguồn thuộc đúng môn, lớp, học kỳ và loại bảng điểm này.</label><button class="primary" id="compare-run" disabled>So Khớp điểm</button></form><section id="comparison-result" aria-live="polite"></section><details><summary>Xem bảng điểm đã ký</summary><iframe src="/api/submissions/${row.id}/pdf?inline=true" title="PDF đối chiếu"></iframe></details>`;
  dialog.showModal();
  const f=form('comparison-form'),mappingHost=document.getElementById('comparison-mapping'),resultHost=document.getElementById('comparison-result');
  let comparisonGeneration=0;
  f.onchange=e=>{if(e.target instanceof HTMLSelectElement&&resultHost)resultHost.innerHTML='';};
  const normalize=/** @param {string} value */value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/đ/g,'d').replace(/\s+/g,' ').trim();
  input('comparison-file').onchange=()=>{void busy(async()=>{
    const generation=++comparisonGeneration;
    const confirmation=f.querySelector('input[type="checkbox"]');if(confirmation instanceof HTMLInputElement)confirmation.checked=false;
    if(mappingHost)mappingHost.innerHTML='';if(resultHost)resultHost.innerHTML='';
    const run=document.getElementById('compare-run');if(run instanceof HTMLButtonElement)run.disabled=true;
    const files=input('comparison-file').files;if(!files?.length)return;
    const data=new FormData();data.set('file',files[0]);data.set('version',String(info.version));
    const source=await api(`/api/submissions/${row.id}/comparison/reference`,{method:'POST',body:data});
    if(generation!==comparisonGeneration)return;
    if(mappingHost)mappingHost.innerHTML=`<p>File nguồn: ${source.student_count} sinh viên. Ghép cột điểm PDF với cột trong file:</p>${info.columns.map(/** @param {{key:string,label:string}} column */column=>`<label>${esc(column.label)}<select data-score-key="${esc(column.key)}"><option value="">Không đối chiếu cột này</option>${source.columns.map(/** @param {{key:string,label:string}} c */c=>`<option value="${esc(c.key)}" ${normalize(c.label)===normalize(column.label)?'selected':''}>${esc(c.label)}</option>`).join('')}</select></label>`).join('')}`;
    if(run instanceof HTMLButtonElement)run.disabled=false;
  });};
  f.onsubmit=e=>{e.preventDefault();void busy(async()=>{
    if(resultHost)resultHost.innerHTML='';
    /** @type {Record<string,string>} */ const pairs={};
    for(const field of f.querySelectorAll('[data-score-key]'))if(field instanceof HTMLSelectElement&&field.value)pairs[field.dataset.scoreKey||'']=field.value;
    if(!Object.keys(pairs).length)throw new Error('Hãy ghép ít nhất một cột điểm.');
    const data=new FormData(f);data.set('version',String(info.version));data.set('mapping',JSON.stringify(pairs));
    const result=await api(`/api/submissions/${row.id}/comparison`,{method:'POST',body:data});
    /** @type {Record<string,string>} */ const labels={match:'Khớp với file nguồn đã chọn',different:'Có sai khác với file nguồn',incomplete:'Chưa đủ dữ liệu để kết luận khớp toàn bộ',missing:'Thiếu trong file nguồn',extra:'Không có trong PDF',unavailable:'Thiếu giá trị điểm',mismatch:'Lệch điểm'};
    if(resultHost)resultHost.innerHTML=`<h3>${esc(labels[result.status])}</h3><p>Đối chiếu ${result.mapped_columns}/${result.total_columns} cột điểm · PDF ${result.pdf_students} SV · Nguồn ${result.reference_students} SV.</p><p>Khớp ${result.matched} · Lệch ${result.mismatched} · Thiếu ${result.missing} · Thừa ${result.extra} · Chưa có điểm ${result.unavailable}.</p>${result.differences.length?`<div class="table-wrap"><table><thead><tr><th>Mã SV / Họ tên</th><th>Kết quả</th><th>PDF đã ký</th><th>PDF xuất từ daotao</th></tr></thead><tbody>${result.differences.map(/** @param {{student_id:string,name:string,type:string,cells:{column:string,pdf:string,reference:string}[]}} difference */difference=>`<tr><td>${esc(difference.student_id)}<small>${esc(difference.name)}</small></td><td>${esc(labels[difference.type])}</td><td>${difference.cells.map(c=>`${esc(c.column)}: ${esc(c.pdf||'(trống)')}`).join('<br>')}</td><td>${difference.cells.map(c=>`${esc(c.column)}: ${esc(c.reference||'(trống)')}`).join('<br>')}</td></tr>`).join('')}</tbody></table></div>`:'<p>Không có dòng sai khác trong các cột đã chọn.</p>'}`;
  },f.querySelector('button'));};
}

/** @param {number} id */
async function detail(id){
  const s=state.items.find(x=>x.id===id),u=state.user;if(!s||!u)return;
  const verification=await api(`/api/submissions/${s.id}/verification`);
  const d=document.getElementById('detail-dialog'),container=document.getElementById('detail');if(!(d instanceof HTMLDialogElement)||!container)return;
  const expired=state.deadline&&new Date(state.deadline)<new Date();
  const head=u.role==='head'&&s.status==='submitted'&&!expired;
  const training=u.role==='training'&&s.status==='head_signed';
  container.innerHTML=`<div class="modal-header"><div><div class="eyebrow">${esc(s.code)} · PHIÊN BẢN ${s.version}</div><h2>${esc(s.title)}</h2></div><button data-action="close" class="secondary" aria-label="Đóng hồ sơ">✕</button></div><p>${esc(s.teacher_name)} · ${esc(s.department)} · HK ${esc(s.semester)} · ${esc(s.year)}</p><div class="modal-actions"><a class="secondary" href="/api/submissions/${s.id}/pdf">Tải PDF để ký / lưu ↧</a><span class="badge ${esc(s.status)}">${esc(statusLabel(s.status))}</span></div><iframe src="/api/submissions/${s.id}/pdf?inline=true" title="Xem trước bảng điểm PDF"></iframe>${s.reason?`<p class="note">Lý do trả: ${esc(s.reason)}</p>`:''}${head?`<form id="head-form" class="decision"><label>PDF đã ký thêm chữ ký trưởng khoa<input type="file" name="file" accept=".pdf,application/pdf" required></label><button class="primary">Nộp đến Phòng Đào tạo →</button></form>`:''}${training?`<button id="archive" class="primary">Xác minh lại và lưu trữ</button>`:''}${head||training?`<form id="reject-form" class="decision"><label>Lý do trả lại<textarea name="reason" required maxlength="2000" placeholder="Nêu rõ nội dung cần giảng viên sửa…"></textarea></label><button class="danger">Trả lại giảng viên</button></form>`:''}`;
  container.querySelector('.modal-actions')?.insertAdjacentHTML('afterend',`<div class="note"><strong>Người ký trên PDF</strong>${signerInfo(verification.signatures)}</div>`);
  container.querySelector('.modal-header')?.insertAdjacentHTML('afterend',`<p><strong>${esc(assessmentTypes[s.assessment_type])}</strong>${s.document_label?' · '+esc(s.document_label):''} · Hồ sơ #${s.id}</p>`);
  d.showModal();
  /** @param {string} url @param {RequestInit} options */
  async function decide(url,options){await api(url,options);d instanceof HTMLDialogElement&&d.close();message('Đã cập nhật hồ sơ.');await loadList();}
  if(head){form('head-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{const data=new FormData(form('head-form'));data.set('version',String(s.version));await decide(`/api/submissions/${s.id}/head-sign`,{method:'POST',body:data});},form('head-form').querySelector('button'));};}
  if(head||training){form('reject-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{await decide(`/api/submissions/${s.id}/reject`,{method:'POST',body:JSON.stringify({version:s.version,reason:new FormData(form('reject-form')).get('reason')})});},form('reject-form').querySelector('button'));};}
  const archive=document.getElementById('archive');if(archive)archive.onclick=()=>{void busy(async()=>decide(`/api/submissions/${s.id}/archive`,{method:'POST',body:JSON.stringify({version:s.version})}),archive);};
}

async function adminView(){
  shell();const [userData,logs,ops,departmentData]=await Promise.all([api('/api/admin/users'),api('/api/admin/audit'),api('/api/admin/operations'),api('/api/admin/departments')]);const users=/** @type {User[]} */(userData);
  /** @typedef {{code:string,name:string,statistical:number}} Department */
  const departments=/** @type {Department[]} */(departmentData);
  const departmentOptions=()=>'<option value="">Chọn khoa / đơn vị</option>'+departments.map(d=>`<option value="${esc(d.code)}">${esc(d.name)} (${esc(d.code)})</option>`).join('');
  content(`<section class="page-heading"><div class="eyebrow">CẤU HÌNH & KIỂM SOÁT</div><h1>Quản trị hệ thống</h1><p>Cấp tài khoản, liên kết chứng thư và cấu hình đợt nộp bảng điểm.</p></section><div class="admin-grid"><section class="records"><h2>Cấp tài khoản trường</h2><form id="user-form"><label>Họ tên<input name="name" required></label><label>Email @vku.udn.vn<input name="email" type="email" required></label><label>Mật khẩu tạm (ít nhất 12 ký tự)<input name="password" type="password" minlength="12" required autocomplete="new-password"></label><label>Vai trò<select name="role">${Object.entries(roles).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>Khoa<input name="department" required></label><label>Fingerprint chứng thư SHA-256<input name="fingerprint" pattern="[a-fA-F0-9]{64}" placeholder="64 ký tự hex; có thể cấu hình sau"></label><button class="primary">Cấp tài khoản</button></form></section><section class="records"><h2>Danh mục từ UIS</h2><form id="course-form"><label>Mã LHP<input name="code" required></label><label>Tên học phần / lớp trên PDF<input name="title" required></label><div class="two"><label>Năm học<input name="year" placeholder="2025-2026" pattern="[0-9]{4}-[0-9]{4}" required></label><label>Học kỳ<select name="semester"><option>1</option><option>2</option><option>3</option></select></label></div><label>Khoa<input name="department" required></label><label>Giảng viên<select name="teacher_id" required><option value="">Chọn giảng viên</option>${users.filter(u=>u.role==='teacher'&&u.active).map(u=>`<option value="${u.id}">${esc(u.name+' · '+u.department)}</option>`).join('')}</select></label><label>PDF tương đối trong UIS_EXPORT_DIR<input name="source_pdf" placeholder="exports/17210.pdf"></label><label>Các mã từ URL UIS (phân cách bằng dấu phẩy)<input name="uis_document_id" pattern="[0-9, ]+" placeholder="17210, 17219"></label><button class="primary">Thêm lớp học phần</button></form></section></div><section class="records"><h2>Thời hạn nộp</h2><form id="deadline-form" class="decision"><label>Ngày giờ kết thúc (giờ máy hiện tại)<input name="deadline" type="datetime-local" required></label><button class="secondary">Lưu thời hạn</button></form><p class="muted">Sau thời hạn, GV và TK chỉ xem và tải. Phòng Đào tạo tiếp tục tiếp nhận hồ sơ đang chờ.</p></section><section class="records"><h2>Tài khoản & chứng thư</h2><div class="table-wrap"><table><thead><tr><th>Người dùng</th><th>Vai trò</th><th>Fingerprint SHA-256</th><th>Trạng thái</th><th></th></tr></thead><tbody>${users.map(u=>`<tr><td>${esc(u.name)}<small>${esc(u.email)}</small></td><td>${esc(roles[u.role])}</td><td><input id="fp-${u.id}" value="${esc(u.fingerprint)}" aria-label="Fingerprint ${esc(u.name)}"></td><td><label class="checkbox"><input id="active-${u.id}" type="checkbox" ${u.active?'checked':''}> Hoạt động</label></td><td><button class="secondary save-user" data-user="${u.id}">Lưu</button></td></tr>`).join('')}</tbody></table></div></section><section class="records"><h2>Nhật ký gần nhất</h2><div class="table-wrap"><table><thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Hồ sơ</th></tr></thead><tbody>${logs.map(/** @param {{created_at:string,user_id:number,action:string,target:string}} l */l=>`<tr><td>${esc(new Date(l.created_at).toLocaleString('vi-VN'))}</td><td>${l.user_id}</td><td>${esc(l.action)}</td><td>${esc(l.target)}</td></tr>`).join('')}</tbody></table></div></section>`);
  /** @param {string} id @param {string} url @param {string} method @param {(d:Record<string,FormDataEntryValue>)=>unknown} transform */
  function bind(id,url,method='POST',transform=d=>d){const f=form(id);f.onsubmit=e=>{e.preventDefault();void busy(async()=>{await api(url,{method,body:JSON.stringify(transform(Object.fromEntries(new FormData(f))))});message('Đã lưu cấu hình.');await adminView();},f.querySelector('button'));};}
  for(const id of ['user-form','course-form']){
    const field=form(id).querySelector('[name=department]');
    if(field)field.outerHTML=`<select name="department" required>${departmentOptions()}</select>`;
  }
  bind('user-form','/api/admin/users');bind('course-form','/api/admin/courses','POST',d=>({...d,teacher_id:Number(d.teacher_id)}));
  bind('deadline-form','/api/admin/deadline','PUT',d=>({deadline:new Date(String(d.deadline)).toISOString()}));
  for(const button of root.querySelectorAll('.save-user')){if(button instanceof HTMLButtonElement)button.onclick=()=>{void busy(async()=>{const id=button.dataset.user;await api('/api/admin/users/'+id,{method:'PATCH',body:JSON.stringify({active:input('active-'+id).checked,fingerprint:input('fp-'+id).value})});if(Number(id)===state.user?.id){state.user=null;loginView();message('Đã cập nhật tài khoản. Vui lòng đăng nhập lại.');}else{message('Đã cập nhật tài khoản và hủy các phiên đăng nhập cũ.');await adminView();}},button);};}
  const contentRoot=document.getElementById('content');
  document.querySelector('.admin-grid')?.insertAdjacentHTML('beforebegin',`<section class="records" id="department-admin"><h2>Danh mục Khoa / Đơn vị</h2><form id="department-form" class="filters"><label>Mã khoa<input name="code" maxlength="100" required></label><label>Tên khoa / đơn vị<input name="name" maxlength="150" required></label><label class="checkbox"><input name="statistical" type="checkbox" checked> Hiển thị trong thống kê khoa</label><button class="primary">Thêm khoa</button></form><div class="table-wrap"><table><thead><tr><th>Mã</th><th>Tên khoa / đơn vị</th><th>Thống kê</th><th>Thao tác</th></tr></thead><tbody>${departments.map(d=>`<tr data-department="${esc(d.code)}"><td>${esc(d.code)}</td><td>${esc(d.name)}</td><td>${d.statistical?'Có':'Không'}</td><td><button type="button" class="secondary edit-department">Sửa</button> <button type="button" class="secondary delete-department">Xóa</button></td></tr>`).join('')}</tbody></table></div></section>`);
  form('department-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{
    const data=new FormData(form('department-form'));await api('/api/admin/departments',{method:'POST',body:JSON.stringify({code:data.get('code'),name:data.get('name'),statistical:data.has('statistical')})});message('Đã thêm khoa.');await adminView();
  },form('department-form').querySelector('button'));};
  for(const row of root.querySelectorAll('#department-admin tbody tr')){
    if(!(row instanceof HTMLElement))continue;
    const d=departments.find(d=>d.code===row.dataset.department);if(!d)continue;
    const edit=row.querySelector('.edit-department'),remove=row.querySelector('.delete-department');
    if(edit instanceof HTMLButtonElement)edit.onclick=()=>{
      const dialog=document.getElementById('detail-dialog'),host=document.getElementById('detail');if(!(dialog instanceof HTMLDialogElement)||!host)return;
      host.innerHTML=`<div class="modal-header"><h2>Sửa khoa / đơn vị</h2><button class="secondary" data-action="close" aria-label="Đóng sửa khoa">✕</button></div><form id="department-edit-form"><label>Mã khoa<input name="code" value="${esc(d.code)}" readonly></label><label>Tên khoa / đơn vị<input name="name" value="${esc(d.name)}" required maxlength="150"></label><label class="checkbox"><input name="statistical" type="checkbox" ${d.statistical?'checked':''}> Hiển thị trong thống kê khoa</label><button class="primary">Lưu khoa</button></form>`;
      form('department-edit-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{const data=new FormData(form('department-edit-form'));await api('/api/admin/departments/'+encodeURIComponent(d.code),{method:'PUT',body:JSON.stringify({code:d.code,name:data.get('name'),statistical:data.has('statistical')})});message('Đã cập nhật khoa.');await adminView();},form('department-edit-form').querySelector('button'));};dialog.showModal();
    };
    if(remove instanceof HTMLButtonElement)remove.onclick=()=>{if(!confirm(`Xóa khoa ${d.name} (${d.code})?`))return;void busy(async()=>{await api('/api/admin/departments/'+encodeURIComponent(d.code),{method:'DELETE'});message('Đã xóa khoa.');await adminView();},remove);};
  }
  const accountTable=root.querySelector('.save-user')?.closest('table');
  if(accountTable){
    accountTable.closest('.table-wrap')?.insertAdjacentHTML('beforebegin','<label>Tìm tài khoản<input id="account-search" placeholder="Họ tên, email, vai trò hoặc khoa"></label>');
    for(const button of accountTable.querySelectorAll('.save-user')){
      if(!(button instanceof HTMLButtonElement))continue;
      const user=users.find(u=>u.id===Number(button.dataset.user));if(!user)continue;
      const row=button.closest('tr');if(!row)continue;row.dataset.account=String(user.id);
      row.children[0]?.insertAdjacentHTML('beforeend',`<small>${esc(departments.find(d=>d.code===user.department)?.name||user.department)}</small>`);
      button.parentElement?.insertAdjacentHTML('beforeend',` <button class="secondary edit-account">Sửa</button> <button class="secondary delete-account" ${user.id===state.user?.id?'disabled':''}>Xóa</button>`);
      const edit=row.querySelector('.edit-account'),remove=row.querySelector('.delete-account');
      if(edit instanceof HTMLButtonElement)edit.onclick=()=>{
        const dialog=document.getElementById('detail-dialog'),host=document.getElementById('detail');if(!(dialog instanceof HTMLDialogElement)||!host)return;
        host.innerHTML=`<div class="modal-header"><h2>Sửa tài khoản trường</h2><button class="secondary" data-action="close" aria-label="Đóng sửa tài khoản">✕</button></div><form id="account-edit-form"><label>Họ tên<input name="name" value="${esc(user.name)}" required maxlength="100"></label><label>Email @vku.udn.vn<input name="email" type="email" value="${esc(user.email)}" required></label><label>Vai trò<select name="role">${Object.entries(roles).map(([code,name])=>`<option value="${code}">${esc(name)}</option>`).join('')}</select></label><label>Khoa<select name="department" required>${departmentOptions()}</select></label><label>Mật khẩu mới (để trống để giữ nguyên)<input name="password" type="password" minlength="12" autocomplete="new-password"></label><label>Fingerprint chứng thư SHA-256<input name="fingerprint" value="${esc(user.fingerprint)}" pattern="[a-fA-F0-9]{64}"></label><label class="checkbox"><input name="active" type="checkbox" ${user.active?'checked':''}> Hoạt động</label><button class="primary">Lưu tài khoản</button></form>`;
        const f=form('account-edit-form');const role=f.querySelector('[name=role]'),dept=f.querySelector('[name=department]');if(role instanceof HTMLSelectElement)role.value=user.role;if(dept instanceof HTMLSelectElement)dept.value=user.department;
        f.onsubmit=e=>{e.preventDefault();void busy(async()=>{const data=new FormData(f);await api('/api/admin/users/'+user.id,{method:'PATCH',body:JSON.stringify({...Object.fromEntries(data),active:data.has('active')})});message('Đã cập nhật tài khoản.');if(user.id===state.user?.id){state.user=null;loginView();message('Đã cập nhật tài khoản. Vui lòng đăng nhập lại.');}else await adminView();},f.querySelector('button'));};dialog.showModal();
      };
      if(remove instanceof HTMLButtonElement)remove.onclick=()=>{if(!confirm(`Xóa tài khoản ${user.name} (${user.email}), vai trò ${roles[user.role]}?`))return;void busy(async()=>{await api('/api/admin/users/'+user.id,{method:'DELETE'});message('Đã xóa tài khoản.');await adminView();},remove);};
    }
    input('account-search').oninput=()=>{const query=input('account-search').value.toLocaleLowerCase('vi');for(const row of accountTable.querySelectorAll('tbody tr'))if(row instanceof HTMLElement)row.hidden=!(row.textContent||'').toLocaleLowerCase('vi').includes(query);};
  }
  if(contentRoot)contentRoot.insertAdjacentHTML('beforeend',`<section class="records"><h2>Tích hợp & sao lưu</h2><p>CA ký số: ${ops.trust_configured?'Đã cấu hình':'Chưa cấu hình APP_TRUST_DIR'} · PDF nguồn UIS: ${ops.uis_export_configured?'Đã cấu hình':'Chưa cấu hình UIS_EXPORT_DIR'}</p><p>Backup định kỳ: ${ops.backup.configured?'Đã cấu hình':'Chưa cấu hình APP_BACKUP_DIR'}<br>Lần thành công gần nhất: ${esc(ops.backup.last_success?new Date(ops.backup.last_success).toLocaleString('vi-VN'):'Chưa có')}${ops.backup.last_error?'<br>Backup gần nhất lỗi. Kiểm tra log vận hành.':''}</p><button id="backup-now" class="secondary" ${ops.backup.configured?'':'disabled'}>Sao lưu ngay</button></section>`);
  const backup=document.getElementById('backup-now');if(backup)backup.onclick=()=>{void busy(async()=>{await api('/api/admin/backup',{method:'POST'});message('Backup đã hoàn tất kèm manifest SHA-256.');await adminView();},backup);};
  const mappingCourses=/** @type {Course[]} */(await api('/api/courses'));
  if(contentRoot)contentRoot.insertAdjacentHTML('beforeend',`<section class="records"><h2>GV ký thứ hai cho bảng điểm cuối kỳ</h2><form id="co-teacher-form"><label>Lớp học phần<select id="co-teacher-course" required><option value="">Chọn lớp</option>${mappingCourses.filter(c=>!guidanceCourse(c.title)).map(c=>`<option value="${c.id}">${esc(c.code+' · '+c.title+' · HK'+c.semester+' '+c.year)}</option>`).join('')}</select></label><label>Giảng viên ký thứ hai<select id="co-teacher-user"><option value="">Chưa phân công</option></select></label><button class="secondary">Lưu GV ký thứ hai</button></form><p class="muted">Cấu hình này chỉ để tham khảo. Hệ thống nhận diện GV ký thứ hai từ PDF, không yêu cầu người đó dạy lớp hay được phân công trước. PDF có hai chữ ký GV khác nhau; trưởng khoa ký thêm chữ ký thứ ba.</p></section>`);
  select('co-teacher-course').onchange=()=>{const c=mappingCourses.find(c=>c.id===Number(select('co-teacher-course').value));select('co-teacher-user').innerHTML='<option value="">Chưa phân công</option>'+users.filter(user=>user.role==='teacher'&&user.active&&user.id!==c?.teacher_id).map(user=>`<option value="${user.id}">${esc(user.name+' · '+user.email)}</option>`).join('');select('co-teacher-user').value=c?.co_teacher_id?String(c.co_teacher_id):'';};
  form('co-teacher-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{const cid=select('co-teacher-course').value;await api(`/api/admin/courses/${cid}/co-teacher`,{method:'PATCH',body:JSON.stringify({co_teacher_id:select('co-teacher-user').value?Number(select('co-teacher-user').value):null})});message('Đã lưu GV ký thứ hai.');await adminView();},form('co-teacher-form').querySelector('button'));};
  if(contentRoot)contentRoot.insertAdjacentHTML('beforeend',`<section class="records"><h2>Liên kết PDF theo loại bảng điểm</h2><form id="mapping-form"><label>Lớp học phần<select id="mapping-course" name="course_id" required><option value="">Chọn lớp</option>${mappingCourses.map(c=>`<option value="${c.id}">${esc(c.code+' · '+c.title)}</option>`).join('')}</select></label><label>Các mã UIS bảng điểm cuối kỳ<input id="mapping-final" name="uis_document_id" pattern="[0-9, ]+"></label><label>Các mã UIS bảng điểm thành phần<input id="mapping-component" name="uis_component_document_id" pattern="[0-9, ]+"></label><button class="secondary">Lưu liên kết bảng điểm</button></form><p class="muted">Nhập một hoặc nhiều mã UIS, phân cách bằng dấu phẩy (ví dụ: 17210, 17219). Mỗi loại có danh sách riêng; để trống thành phần sẽ dùng danh sách cuối kỳ. Chỉ nhập mã được phép cho lớp này.</p></section>`);
  select('mapping-course').onchange=()=>{const c=mappingCourses.find(c=>c.id===Number(select('mapping-course').value));input('mapping-final').value=c?.uis_document_id||'';input('mapping-component').value=c?.uis_component_document_id||'';};
  form('mapping-form').onsubmit=e=>{e.preventDefault();void busy(async()=>{const cid=select('mapping-course').value;await api(`/api/admin/courses/${cid}/mappings`,{method:'PATCH',body:JSON.stringify({uis_document_id:input('mapping-final').value,uis_component_document_id:input('mapping-component').value})});message('Đã lưu liên kết cho từng loại bảng điểm.');await adminView();},form('mapping-form').querySelector('button'));};
}

void (async()=>{try{const data=await api('/api/me');state.user=data.user;state.csrf=data.csrf;await dashboard();}catch{loginView();}})();
