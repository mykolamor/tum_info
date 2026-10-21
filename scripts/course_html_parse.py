from bs4 import BeautifulSoup
import sys
import re
import os
import os.path
import course_functions

def logger(message):
  print(message)

args = sys.argv
soup = None

with open(args[1]) as fp:
    soup = BeautifulSoup(fp, 'html.parser')

courses = soup.find_all('h3')
logger('Found {} courses.'.format(len(courses)))

def process_achievement(course):
  achievement = dict()
  header = course.string.strip().replace('\r', '').replace('\n', '')
  header_regex = r"^([0-9\-]+) - ([\w-]+) (.+) \(([\d.]+)SWS .+ ([WS])S 20(\d+)/(\d+)\)$"
  header_match = re.search(header_regex, header)
  if header_match == None:
    raise Exception(header)
  header_number = header_match.group(2)
  header_number_regex = r"^([A-Z]+).+$"
  header_dep = re.search(header_number_regex, header_number).group(1)
  header_school = None
  if header_dep in course_functions.schools:
    header_school = course_functions.schools[header_dep]
  else:
    logger('Unknown course dep: {}'.format(header_dep))
    header_school = header_dep
  header_sem = header_match.group(6) if header_match.group(5) == 'W' else header_match.group(7)
  header_hours = float(header_match.group(4))
  
  if header_hours in course_functions.ects:
    header_ects = course_functions.ects[header_hours]
  else:
    logger('Unknown SWS: {}'.format(header_hours))
    header_ects = header_hours

  achievement = {
    'id': 0,
    'href': '',
    'mode': 'written',
    'date': '{} 12:00:00 +0100'.format(header_match.group(1)),
    'number': header_number,
    'name': header_match.group(3),
    'type': 'endterm',
    'semester': '20{}S'.format(header_sem + header_match.group(5)),
    'hours': header_hours,
    'ects': header_ects,
    'school': header_school,
  }

  grade_elem = next(filter(lambda x: x.name == 'div', course.next_siblings), None)
  grade_list = grade_elem.find_all('div', class_='kandcountbox')
  
  achievement = process_grades(achievement, grade_list)
  return achievement
  
def process_grades(achievement, grade_list):
  grades = dict()
  for grade_elem in grade_list:
    grade_people_elem = next(filter(lambda x: x.name == 'div', grade_elem.next_siblings), None)
    grade_people_text = grade_people_elem.contents[-1].strip()
    grade_people_regex = r"^(\d+) K.$"
    grade_people = int(re.search(grade_people_regex, grade_people_text).group(1))
    if grade_people == 0:
      continue

    grade_value_elem = next(filter(lambda x: x.name == 'div', grade_people_elem.next_siblings), None)
    grade_value_text = grade_value_elem.div.contents[-1].strip()
    grade_value = 0.0
    # X didn't show up
    # U cheated
    # Q withdrew
    # Z rejected
    # B passed without grade
    # N didn't pass without grade
    if 'X' in grade_value_text:
      grade_value = 6.0
    elif 'U' in grade_value_text:
      grade_value = 5.0
      achievement['cheated'] = grade_people
    elif 'Z' in grade_value_text:
      grade_value = 5.0
      achievement['rejected'] = grade_people
    elif 'Q' in grade_value_text:
      achievement['withdrew'] = grade_people
      continue
    elif 'B' in grade_value_text:
      grade_value = 7.0
      achievement['pass'] = grade_people
    elif 'N' in grade_value_text:
      grade_value = 8.0
      achievement['fail'] = grade_people
    else:
      try:
        grade_value = float(grade_value_text.replace(',', '.'))
      except:
        logger('Failed to parse {}. Contact mykolamor.'.format(grade_value_text))
        achievement['grades'] = None
        return achievement
    
    grades[grade_value] = {
        'value': grade_value,
        'count': grade_people,
      }

  achievement['grades'] = list(grades.values())
  achievement['grades'].sort(key=lambda x: x['value'])
  return achievement

for course in courses:
  achievement = process_achievement(course)
  if achievement['grades'] == None or len(achievement['grades']) == 0 or course_functions.achievement_exists(achievement, logger, True):
    continue
  course_functions.achievement_save(achievement, logger, True)
