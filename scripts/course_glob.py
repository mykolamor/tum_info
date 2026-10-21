import sys
import os
import course_functions

def logger(message):
  print(message)

args = sys.argv
list_name = list(filter(lambda x: x.startswith('name='),args))
list_pass = list(filter(lambda x: x.startswith('pass='),args))
if ('-h' in args or
    len(list_name) == 0 or
    len(list_pass) == 0):
  logger('''scripts/course_glob.py name=ab12cde@mytum.de pass=42424242 [-h -v]
name=<> Verbatim TUMOnline login name. Can be email or whatever it accepts.
pass=<> Password corresponding to the name.
-h Print this help message.
-v Verbose output.
Check script source if a school mapping is missing.
If unsure about abbreviation, check tum.de subdomain.
''')
  exit(0)

user_name = list_name[0][5:]
user_pass = list_pass[0][5:]
verbose = len(list(filter(lambda x: x.startswith('-v'),args))) > 0

# This script does:
# - acquire a temporary session id and access token to load your data
# - load a list of your achievements to extract statistics
# - load each achievement to extract course properties
# - load exam statistics for each exam date to extract the grade distribution
# - save exam statistics to disk
# This script does not:
# - send your login/password/session/token anywhere outside TUMOnline
# - store your personal data anywhere, apart from the info gathered for the website
#   **Note**: your info remains on your machine until you commit and push the changes
# - expose sensitive data or print it in full form anywhere outside the python environment
#   **Warn**: verbose output option would partially show ids and tokens
# - expose achievement data outside the python environment and the host (terminal/pipe)

# Check working directory
if os.path.isfile('./scripts/course_glob.py') == False:
  logger('Wrong working directory. Execute from repository root.')
  exit(1)

logger('Found correct working directory.')

logger('Performing login...')
auth = course_functions.perform_login(user_name, user_pass, logger, verbose)
logger('Performing profile lookup...')
auth = course_functions.perform_profile(auth, logger, verbose)
logger('Performing achievements lookup...')
achievements = course_functions.perform_achievements(auth, logger, verbose)
logger('Performing grade stats lookup...')
# Each achievement yields one entry per exam date (endterm, retake)
achievements = [y for x in achievements for y in course_functions.perform_exam(auth, x, logger, verbose)]
achievements = list(filter(lambda x: course_functions.achievement_exists(x, logger, verbose) == False, achievements))
logger('Performing grade stats save...')
achievements = list(map(lambda x: course_functions.achievement_save(x, logger, verbose), achievements))
logger('Finished.')
