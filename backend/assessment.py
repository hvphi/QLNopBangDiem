import re
import unicodedata


def guidance_course(title):
    title = ' '.join(unicodedata.normalize('NFC', title).casefold().split())
    return bool(re.search(r'(?<!\w)(?:đồ án|đề án|thực tập|kiến tập)(?!\w)', title))


def requires_two_teachers(course, assessment_type):
    return assessment_type == 'final' and not guidance_course(course['title'])
