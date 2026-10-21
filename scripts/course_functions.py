# TODO: if script complains, update this dict and rerun
# Mapping of departments to schools.
schools = {
  'IN': 'CIT',
  'MA': 'CIT',
  'EI': 'CIT',
  'CIT': 'CIT',
  'WI': 'MGT',
  'MGT': 'MGT',
  'SZ': 'SZ',
  'MW': 'ED',
  'BV': 'ED',
  'CLA': 'SOT',
  'ED': 'SOT',
  'SOT': 'SOT',
  'MCTS': 'MCTS',
  'POL': 'MCTS',
  'ME': 'MED',
  'PH': 'NAT',
  'ASG': 'ED',
  'LRG': 'ED',
  'FSD': 'ED',
}
# Mapping of semester working hours to ECTS.
ects = {
  0.0: 1,
  0.5: 1,
  1.0: 2,
  1.5: 3,
  2.0: 3,
  3.0: 4,
  4.0: 5,
  5.0: 7,
  6.0: 8,
  7.0: 9,
  9.0: 10,
}

import os
import os.path
import requests # for http communication
from urllib.parse import urlparse, parse_qs, urljoin # for redirect url parsing
from html.parser import HTMLParser # for login form parsing
from datetime import datetime # for achievement date parsing
import re # for course number parsing
import base64, hashlib, secrets, uuid # for oauth pkce

url_base = 'https://campus.tum.de/tumonline'
url_oidc = url_base + '/co/public/sec/auth/realms/CAMPUSonline_SP/protocol/openid-connect'
url_desktop = url_base + '/ee/ui/ca2/app/desktop/'
url_achievements = url_base + '/co/co-xm-ac-app/app/achievements'
# Keycloak clients as (client id, redirect uri), same as the browser apps use.
client_desktop = ('co-desktop-user', url_desktop + '#/login?')
client_achievements = ('co-xm-ac-app-user', url_base + '/co/co-xm-ac-app/app/assets/silent-check-sso.html')

# Headers copied from a Firefox trace, so the requests look like the browser ones.
head_navigate = {
  'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:158.0) Gecko/20100101 Firefox/158.0',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'same-origin',
  'Upgrade-Insecure-Requests': '1',
}
head_cors = {
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-origin',
}
head_ee = dict(head_cors, **{
  'Accept': 'application/json',
  'Accept-Language': 'en',
  'Referer': url_desktop,
})

class AuthModel:
  # cookie is PSESSIONID, token is the achievements app access token.
  # The ee token (exam statistics) is derived from the cookie on demand.
  def __init__(self, cookie, token):
    self.session = requests.Session()
    self.session.headers.update(head_navigate)
    if cookie:
      self.session.cookies.set('PSESSIONID', cookie, domain='campus.tum.de', path='/tumonline/')
    self.token = token
    self.ee_token = None
    self.logged_in = False

def error(logger, message):
  logger(message)
  raise Exception(message)

# Collects forms with their fields and links with ids from an html page
class PageParser(HTMLParser):
  def __init__(self):
    super().__init__()
    self.forms = []
    self.links = {}

  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)
    if tag == 'form':
      self.forms.append({ 'action': attrs.get('action') or '', 'fields': {} })
    elif tag == 'input' and len(self.forms) > 0 and 'name' in attrs and 'disabled' not in attrs:
      if attrs.get('type') in ('checkbox', 'radio') and 'checked' not in attrs:
        return
      self.forms[-1]['fields'][attrs['name']] = attrs.get('value') or ''
    elif tag == 'a' and 'id' in attrs and 'href' in attrs:
      self.links[attrs['id']] = attrs['href']

def parse_page(text):
  parser = PageParser()
  parser.feed(text)
  return parser

# Returns (verifier, challenge) for oauth pkce
def make_pkce():
  verifier = secrets.token_urlsafe(64)
  challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
  return verifier, challenge

def oidc_params(client, challenge, silent):
  params = {
    'client_id': client[0],
    'redirect_uri': client[1],
    'state': str(uuid.uuid4()),
    'response_mode': 'fragment',
    'response_type': 'code',
    'scope': 'openid',
    'nonce': str(uuid.uuid4()),
    'code_challenge': challenge,
    'code_challenge_method': 'S256',
  }
  if silent:
    params['prompt'] = 'none'
  return params

# Keycloak returns the authorization code in the fragment of a redirect location
def find_code(response):
  for r in response.history + [response]:
    fragment = parse_qs(urlparse(r.headers.get('location', '')).fragment)
    if 'code' in fragment:
      return fragment['code'][0]
  return None

def oidc_token(auth, client, code, verifier, referer, logger):
  res_token = auth.session.post(url_oidc + '/token',
    headers=dict(head_cors, **{ 'Accept': '*/*', 'Origin': 'https://campus.tum.de', 'Referer': referer }),
    data={
      'code': code,
      'grant_type': 'authorization_code',
      'client_id': client[0],
      'redirect_uri': client[1],
      'code_verifier': verifier,
    })
  if res_token.status_code != 200:
    error(logger, 'Auth token {}: received bad status {}'.format(client[0], res_token.status_code))
  return res_token.json()['access_token']

# Walk through the TUM IdP pages (login.tum.de) until it redirects back to TUMonline
def idp_login(auth, res_page, username, password, logger, verbose):
  sent_password = False
  for _ in range(5):
    if urlparse(res_page.url).hostname != 'login.tum.de':
      return res_page
    if res_page.status_code != 200:
      error(logger, 'IdP login: received bad status {}'.format(res_page.status_code))
    form = next(filter(lambda x: 'execution=' in x['action'], parse_page(res_page.text).forms), None)
    if form == None:
      error(logger, 'IdP login: no login form found on {}'.format(urlparse(res_page.url).path))
    data = form['fields']
    if 'j_password' in data:
      if sent_password:
        error(logger, 'IdP login: wrong username or password')
      data.update({ 'j_username': username, 'j_password': password, '_eventId_proceed': '' })
      sent_password = True
    elif 'shib_idp_ls_supported' in data:
      # Page normally filled by javascript reporting browser local storage support
      for key in data:
        if key.startswith('shib_idp_ls_success.'):
          data[key] = 'true'
      data['shib_idp_ls_supported'] = 'true'
    else:
      error(logger, 'IdP login: unsupported login step (two-factor?) with fields {}'.format(', '.join(data)))
    if verbose:
      logger('IdP login: submitting {}'.format(urlparse(form['action']).query))
    res_page = auth.session.post(urljoin(res_page.url, form['action']),
      headers={ 'Origin': 'https://login.tum.de', 'Referer': res_page.url },
      data=data)
  error(logger, 'IdP login: too many steps')

def ee_refresh(auth, logger, verbose):
  res_refresh = auth.session.post(url_base + '/ee/rest/auth/token/refresh',
    headers=dict(head_ee, **{ 'Content-Type': 'application/json', 'Origin': 'https://campus.tum.de' }))
  if res_refresh.status_code == 201:
    auth.ee_token = res_refresh.json()['accessToken']
  elif res_refresh.status_code != 204 or auth.ee_token == None:
    error(logger, 'Auth ee token: received bad status {}'.format(res_refresh.status_code))
  if verbose:
    logger('Auth ee token: {}...'.format(auth.ee_token[0:20]))

# GET from the ee rest api, refreshing the short-lived token if needed
def ee_get(auth, url, logger, verbose):
  if auth.ee_token == None:
    ee_refresh(auth, logger, verbose)
  res = auth.session.get(url, headers=dict(head_ee, Authorization='Bearer {}'.format(auth.ee_token)))
  if res.status_code == 401:
    ee_refresh(auth, logger, verbose)
    res = auth.session.get(url, headers=dict(head_ee, Authorization='Bearer {}'.format(auth.ee_token)))
  return res

# Silently get an achievements app token using the keycloak session from the login
def achievements_token(auth, logger, verbose):
  verifier, challenge = make_pkce()
  res_auth = auth.session.get(url_oidc + '/auth',
    headers={ 'Referer': url_achievements, 'Sec-Fetch-Dest': 'iframe' },
    params=oidc_params(client_achievements, challenge, True),
    allow_redirects=False)
  code = find_code(res_auth)
  if code == None:
    error(logger, 'Auth achievements: no code received, status {}'.format(res_auth.status_code))
  auth.token = oidc_token(auth, client_achievements, code, verifier, url_achievements, logger)
  if verbose:
    logger('Auth achievements token: {}...'.format(auth.token[0:20]))

# GET from the achievements app api, renewing the token once if it expired
def achievements_get(auth, url, referer, logger, verbose, params=None):
  if auth.token == None:
    achievements_token(auth, logger, verbose)
  head = dict(head_cors, **{ 'Accept': 'application/json, text/plain, */*', 'Referer': referer })
  res = auth.session.get(url, params=params, headers=dict(head, Authorization='Bearer {}'.format(auth.token)))
  if res.status_code == 401 and auth.logged_in:
    achievements_token(auth, logger, verbose)
    res = auth.session.get(url, params=params, headers=dict(head, Authorization='Bearer {}'.format(auth.token)))
  return res

# Perform initial login into the system
def perform_login(username, password, logger, verbose):
  auth = AuthModel(None, None)

  # Start the keycloak login as the desktop app does. It redirects to a page with an IdP choice.
  verifier, challenge = make_pkce()
  res_page = auth.session.get(url_oidc + '/auth',
    headers={ 'Referer': url_base + '/co/co-desktop/app/login?post_login_base=ee&post_login_route=%2Flogin%3F&onboarding=false' },
    params=oidc_params(client_desktop, challenge, False))
  if res_page.status_code != 200:
    error(logger, 'Auth start: received bad status {}'.format(res_page.status_code))
  idp_link = parse_page(res_page.text).links.get('social-tumidpoidc')
  if idp_link == None:
    error(logger, 'Auth start: TUM login link not found')

  # Follow the TUM IdP link and log in there. Keycloak then redirects back with a code.
  res_page = auth.session.get(urljoin(res_page.url, idp_link))
  res_page = idp_login(auth, res_page, username, password, logger, verbose)
  code = find_code(res_page)
  if code == None:
    error(logger, 'Auth redirect: no code received, status {}'.format(res_page.status_code))
  if 'PSESSIONID' not in auth.session.cookies:
    error(logger, 'Auth redirect: no session cookie received')
  if verbose:
    logger('Session cookie: {}...'.format(auth.session.cookies['PSESSIONID'][0:40]))

  # Finish the desktop login like the browser does, then receive the ee access token
  oidc_token(auth, client_desktop, code, verifier, res_page.url, logger)
  auth.logged_in = True
  ee_refresh(auth, logger, verbose)

  return auth

# Switch to the student profile
def perform_profile(auth, logger, verbose):
  if auth.ee_token == None:
    ee_refresh(auth, logger, verbose)
  res_profile = auth.session.post(url_base + '/ee/rest/auth/profile',
    headers=dict(head_ee, **{ 'Authorization': 'Bearer {}'.format(auth.ee_token), 'Origin': 'https://campus.tum.de' }),
    data={ 'pProfileKey': 'STUDENT', 'profile_key': 'STUDENT' })
  if res_profile.status_code != 200:
    error(logger, 'Auth profile: received bad status {}'.format(res_profile.status_code))

  # The new session cookie comes in the body instead of a header
  res_profile_json = res_profile.json()
  if 'cookie' in res_profile_json:
    auth.session.cookies.set('PSESSIONID', res_profile_json['cookie']['value'], domain='campus.tum.de', path='/tumonline/')
  auth.ee_token = res_profile_json.get('accessToken', auth.ee_token)
  ee_refresh(auth, logger, verbose)
  if verbose:
    logger('Session cookie: {}...'.format(auth.session.cookies['PSESSIONID'][0:40]))

  return auth

# Gather and filter all achievements
def perform_achievements(auth, logger, verbose):
  res_achieve_list = []
  page = 0
  while True:
    res_achieve = achievements_get(auth, url_base + '/co/co-xm-ac-app/api/achievements',
      url_achievements + '?f_status_types=FINAL&q=&sort=desc&page={}'.format(page), logger, verbose,
      params={ 'status_types': 'FINAL', 'sort': 'desc', 'page': page, 'page_size': 25, 'lang_key': 'en' })
    if res_achieve.status_code != 200:
      error(logger, 'Achievements: received bad status {}'.format(res_achieve.status_code))
    res_achieve_json = res_achieve.json()
    res_achieve_list += res_achieve_json['items']
    page += 1
    if len(res_achieve_json['items']) == 0 or len(res_achieve_list) >= res_achieve_json['totalItems']:
      break
  # Theses and graduations have no course number
  res_achieve_list = list(filter(lambda o: o['statusType'] == 'FINAL' and 'courseNumber' in o, res_achieve_list))
  if verbose:
    logger('Achievements: {} items initial'.format(len(res_achieve_list)))

  def translated(o):
    return o['value'].get('en') or o['value'].get('de')

  def mapping(o):
    name = translated(o['title'])
    try:
      res_detail = achievements_get(auth, url_base + '/co/co-xm-ac-app/api/achievements/{}'.format(o['uid']),
        url_achievements + '/{}'.format(o['uid']), logger, verbose)
      if res_detail.status_code != 200:
        raise Exception('Received bad status {}'.format(res_detail.status_code))
      d = res_detail.json()
      if d['achievementTypeEnum'] != 'EXAM':
        return None

      name = translated(d['achievementTitle'])
      date = datetime.strptime(d['achievementDate'], '%Y-%m-%d')
      semester_match = re.search(r"(Winter|Summer) semester (\d{4})", d['courseSemesterName']['value']['en'])
      if semester_match == None:
        raise Exception('Unknown semester: {}'.format(d['courseSemesterName']['value']['en']))
      semester = '{}{}'.format(semester_match.group(2), 'WS' if semester_match.group(1) == 'Winter' else 'SS')
      course_type = re.search(r"\((\w+)\)", d['courseTypeName']['value']['de']).group(1)
      if course_type != 'FA':
        raise Exception('Wrong course type: {}'.format(course_type))
      stats_match = re.search(r"examStatistics/(\d+)", d.get('examStatisticsLink') or '')
      if stats_match == None:
        raise Exception('No exam statistics link')
      course_number_regex = r"^([A-Z]+).+$"
      course_number = d['courseNumber']
      course_dep = re.search(course_number_regex, course_number).group(1)
      if course_dep in schools:
        course_school = schools[course_dep]
      else:
        logger('Unknown course dep: {}'.format(course_dep))
        course_school = course_dep
      exam_type = 'endterm'

      return {
        'href': url_base + '/ee/rest/slc.xm.exs/examStatistics/{}'.format(stats_match.group(1)),
        'id': d['uid'],
        'name': name,
        'type': exam_type,
        'date': date.strftime("%Y-%m-%d 12:00:00 +0100"),
        'semester': semester,
        'hours': d['courseHours'],
        'ects': d['credits'],
        'school': course_school,
        'number': course_number,
        'mode': translated(d['examMode']).lower(),
      }
    except Exception as e:
      logger('Failed to parse: {}. {}'.format(name, e))
      return None

  res_achieve_list = list(filter(lambda o: o != None, map(mapping, res_achieve_list)))
  if verbose:
    logger('Achievements: {} items filtered'.format(len(res_achieve_list)))

  return res_achieve_list

# Load info related to a specific exam attempt
# Exam dates closer than this to each other are parallel groups rather than endterm and retake
retake_gap_days = 28

# Returns one achievement per exam with grades: the first exam date is the endterm, one at least
# retake_gap_days later is the retake. Of parallel groups only the default one (your own) is used.
def perform_exam(auth, achievement, logger, verbose):
  # Without an exam id the statistics are for a default exam date (seemingly your own), along with all dates
  res_achieve = ee_get(auth, achievement['href'], logger, verbose)
  if res_achieve.status_code != 200:
    error(logger, 'Achievement {} grade: received bad status {}'.format(achievement['id'], res_achieve.status_code))
  res_achieve_json = res_achieve.json()
  res_achieve_grades = res_achieve_json['gradeEntries']
  default_id = res_achieve_grades[0]['exExamDateId'] if len(res_achieve_grades) > 0 else None

  # The exam title starts with its date, e.g. "23.02.2023 Netzsicherheit"
  exams = res_achieve_json.get('examEntries') or []
  for exam in exams:
    exam['date'] = datetime.strptime(exam['courseTitle'][0:10], '%d.%m.%Y')
  exams.sort(key=lambda x: x['date'])

  # Split the dates into groups that start at least retake_gap_days apart
  groups = []
  for exam in exams:
    if len(groups) == 0 or (exam['date'] - groups[-1][0]['date']).days >= retake_gap_days:
      groups.append([])
    groups[-1].append(exam)
  if len(groups) > 2:
    logger('{} {}: {} exam periods, only the first two are saved'.format(achievement['number'], achievement['name'], len(groups)))

  chosen = []
  for group in groups[0:2]:
    exam = group[0] if len(group) == 1 else next(filter(lambda x: x['id'] == default_id, group), None)
    if exam == None:
      logger('{} {}: {} parallel exams on {}, skipped'.format(achievement['number'], achievement['name'], len(group),
        ', '.join(map(lambda x: x['courseTitle'][0:10], group))))
    chosen.append(exam)

  results = []
  for index, exam in enumerate(chosen):
    if exam == None:
      continue
    if exam['id'] == default_id:
      exam_grades = res_achieve_grades
    else:
      res_exam = ee_get(auth, '{}/{}'.format(achievement['href'], exam['id']), logger, verbose)
      if res_exam.status_code != 200:
        error(logger, 'Achievement {} exam {} grade: received bad status {}'.format(achievement['id'], exam['id'], res_exam.status_code))
      exam_grades = res_exam.json()['gradeEntries']
    if len(exam_grades) == 0:
      continue
    if verbose:
      logger('{} {}: {} grades on {}'.format(achievement['number'], exam['id'], len(exam_grades), exam['courseTitle'][0:10]))

    exam_achievement = dict(achievement)
    exam_achievement['type'] = 'endterm' if index == 0 else 'retake'
    exam_achievement['date'] = exam['date'].strftime("%Y-%m-%d 12:00:00 +0100")
    results.append(process_grades(exam_achievement, exam_grades, logger))

  return results

# Count grades into the achievement
def process_grades(achievement, res_achieve_grades, logger):
  grades = dict()
  for o in res_achieve_grades:
    value = 0.0
    if 'gradeCommentShortName' in o or not o['gradeShortName'][0].isdigit():
      # X didn't show up
      # U cheated
      # Q withdrew
      # Z rejected
      # B passed without grade
      # N didn't pass without grade
      short_name = o.get('gradeCommentShortName') or o['gradeShortName']
      if short_name == 'X':
        value = 6.0
      elif short_name == 'U':
        if 'cheated' not in achievement:
          achievement['cheated'] = 0
        achievement['cheated'] += 1
        value = 5.0
      elif short_name == 'Z':
        if 'rejected' not in achievement:
          achievement['rejected'] = 0
        achievement['rejected'] += 1
        value = 5.0
      elif short_name == 'Q':
        if 'withdrew' not in achievement:
          achievement['withdrew'] = 0
        achievement['withdrew'] += 1
        continue
      elif short_name == 'B':
        if 'pass' not in achievement:
          achievement['pass'] = 0
        achievement['pass'] += 1
        value = 7.0
      elif short_name == 'N':
        if 'fail' not in achievement:
          achievement['fail'] = 0
        achievement['fail'] += 1
        value = 8.0
      else:
        logger('TODO: report to mykolamor - unknown type {}'.format(short_name))
        continue
    else:
      value = float(o['gradeShortName'].replace(',', '.'))

    if value not in grades:
      grades[value] = {
        'value': value,
        'count': 0,
      }
    
    grades[value]['count'] += 1
  
  achievement['grades'] = list(grades.values())
  achievement['grades'].sort(key=lambda x: x['value'])

  return achievement

# Check if an achievement exists; if not, create the dir as a side-effect
def achievement_exists(achievement, logger, verbose):
  path_dir = '_courses/{}/{}'.format(achievement['school'], achievement['number'])
  path_file = '{}/{}-{}.md'.format(path_dir, achievement['semester'], achievement['type'])
  if os.path.isdir(path_dir):
    if os.path.isfile(path_file):
      logger('{} {} {} exists. Check endterm/retake. If wrong, add manually.'.format(
        achievement['number'], achievement['name'], achievement['type']))
      return True
    return False
  os.makedirs(path_dir, exist_ok = True)
  return False

def achievement_save(achievement, logger, verbose):
  path_dir = '_courses/{}/{}'.format(achievement['school'], achievement['number'])
  path_file = '{}/{}-{}.md'.format(path_dir, achievement['semester'], achievement['type'])
  text_grades = list(map(lambda x: '  - {{ grade: {0}, people: {1} }}\n'.format(x['value'], x['count']), achievement['grades']))
  text_desc = ''
  if 'cheated' in achievement:
    text_desc += '{} people cheated. Added to 5.0 column. '.format(achievement['cheated'])
  if 'withdrew' in achievement:
    text_desc += '{} people withdrew. Not present on the plot. '.format(achievement['withdrew'])
  if 'rejected' in achievement:
    text_desc += '{} people rejected. Added to 5.0 column. '.format(achievement['rejected'])
  if 'pass' in achievement:
    text_desc += '{} people passed without a grade. Added to 7.0 column. '.format(achievement['pass'])
  if 'fail' in achievement:
    text_desc += '{} people failed without a grade. Added to 8.0 column. '.format(achievement['fail'])
  text_file = '''---
layout: course

school: "{school}"
code: "{number}"
semester: "{semester}" # refers to the year of the semester start
exam_type: "{type}"
name: "{name}"
date: "{date}"

ects: {ects}
hours: {hours} # semester hours
mode: "{mode}"
lang: "en"

title: "{name} {semester} {type_cap}"
grades:
{grades}
---

{desc}
'''.format(school=achievement['school'], number=achievement['number'].upper(),
    semester=achievement['semester'], type=achievement['type'],
    name=achievement['name'].replace('"', '\\"'), date=achievement['date'],
    ects=achievement['ects'], hours=achievement['hours'],
    mode=achievement['mode'], type_cap=achievement['type'].capitalize(),
    grades=''.join(text_grades), desc=text_desc)
  
  with open(path_file, 'w') as f:
    f.write(text_file)
    logger('Wrote {} {} {}. Check endterm/retake filename and field in file. Check exam_type, mode, lang fields in file.'.format(
      achievement['number'], achievement['name'], achievement['type']))
  return achievement
