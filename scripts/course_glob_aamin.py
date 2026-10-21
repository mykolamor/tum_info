from bs4 import BeautifulSoup
import sys
import re
import requests
import os
import os.path
import course_functions

def logger(message):
  print(message)

args = sys.argv
soup = None

website_response = requests.get('https://stats.aamin.dev/')
if website_response.status_code != 200:
  m = 'Failed to get data from the website'
  logger(m)
  raise Exception(m)

soup = BeautifulSoup(website_response.text, 'html.parser')

courses = soup.find_all("div", {"class": "stats"})
logger('Found {} courses.'.format(len(courses)))

def process_achievement(course):
  achievement = dict()

  header_table = course.table.tbody.find_all('tr')
  table_date = header_table[0].find_all('td')[1].string.strip()
  table_number = header_table[1].find_all('td')[1].string.strip()
  table_number_regex = r"^([A-Z]+).+$"
  table_dep = re.search(table_number_regex, table_number).group(1)
  table_school = None
  if table_dep in course_functions.schools:
    table_school = course_functions.schools[table_dep]
  else:
    logger('Unknown course dep: {}'.format(table_dep))
    table_school = table_dep

  header = course.h3.string.strip().replace('\r', '').replace('\n', '')
  header_regex = r"^(.+) \(([\d.]+)SWS .+ ([WS])S 20(\d+)\/(\d+)\)$"
  header_match = re.search(header_regex, header)
  if header_match == None:
    header = '{} (4SWS FA, {})'.format(header, preprocess_semester(table_date))
    header_match = re.search(header_regex, header)
    if header_match == None:
      logger('{} parsed incompletely. Please ask mykolamor to fix it.'.format(header))
  
  header_name = str(header_match.group(1)).replace('&', 'and').replace('"', '\'')
  header_sem = header_match.group(4) if header_match.group(3) == 'W' else header_match.group(5)
  header_hours = float(header_match.group(2))
  
  if header_hours in course_functions.ects:
    header_ects = course_functions.ects[header_hours]
  else:
    logger('Unknown SWS: {}'.format(header_hours))
    header_ects = header_hours

  achievement = {
    'id': 0,
    'href': '',
    'mode': 'written',
    'date': '{} 12:00:00 +0100'.format(table_date),
    'number': table_number,
    'name': header_name,
    'type': 'endterm',
    'semester': '20{}S'.format(header_sem + header_match.group(3)),
    'hours': header_hours,
    'ects': header_ects,
    'school': table_school,
  }

  grade_elem = course.div
  grade_list = grade_elem.find_all('div', recursive=False)[2:]
  
  achievement = process_grades(achievement, grade_list)
  return achievement

def preprocess_semester(date):
  year = int(date[0:4])
  month = int(date[5:7])
  if month < 5:
    return 'WS {}/{}'.format(str(year - 1), str(year)[2:4])
  elif month > 10:
    return 'WS {}/{}'.format(str(year), str(year + 1)[2:4])
  else:
    return 'SS {}/{}'.format(str(year - 1), str(year)[2:4])

def process_grades(achievement, grade_list):
  grades = dict()
  for grade_elem in grade_list:
    grade_elem_child = grade_elem.find_all('div', recursive=False)
    grade_people_elem = ' '.join(list(grade_elem_child[0].div.stripped_strings))
    grade_people_regex = r"(\d+) K\."
    grade_people = int(re.search(grade_people_regex, grade_people_elem).group(1))
    if grade_people == 0:
      continue

    grade_value_text = ' '.join(list(grade_elem_child[1].stripped_strings))
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
    # B is passed without a grade, N is failed without a grade, for electives and such
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
