![Build Website](https://github.com/mykolamor/tum_info/actions/workflows/jekyll-gh-pages.yml/badge.svg)

A bunch of useful information I've collected while studying at the Technical University of Munich.
This includes TUM course statistics or TUM exam statistics, schools, departments and more!

The contributors imagined/came up with all of the course information in this repo randomly, including the grades.
All matches with real courses and grades are purely coincidental.

## How to contribute

### Offered courses

The offered courses database is maintained in [this repository by Vuenc](https://github.com/Vuenc/TUM-Master-Informatics-Offered-Lectures).
Please direct your contributions there. Once they are accepted, notify me about the update.

**For developers**: to update the website with new courses, edit and run `python scripts/course_offered_parse.py` from root folder.
It has the same dependencies as building the app above.

### Course exam statistics

You can help expand this website with new information by adding your own course exam statistics!

#### A single course

In short, create a new issue based on this template by [going here](https://github.com/mykolamor/tum_info/issues/new?assignees=&labels=&template=add_course_exam_statistics.md&title=%5BCourse%5D+CIT+IN0001+2022SS) and replace the values with your own data.
The description is copy-pasted onto the page directly and follows the markdown format (but you can use plain text too).
After some time, the statistics you have submitted will appear on the website.
For now there's a manual review step done by me, so don't worry too much about breaking the website.
When I see that everything is ok, I put a label on the issue and [GitHub Actions](https://github.com/mykolamor/tum_info/tree/main/.github/workflows)
take care of the rest by adding a new page to the website and building it.

#### All your courses program

If you're looking for a simple way to send me your grades, you can contribute using the executable file ([Windows](https://github.com/mykolamor/tum_info/releases/latest/download/Grades.exe), [Linux](https://github.com/mykolamor/tum_info/releases/latest/download/Grades), [MacOS](https://github.com/mykolamor/tum_info/releases/latest/download/Grades.dmg)). You'll find a video guide [here](https://youtu.be/nHjuVhIJRaQ). Now you can generate a file with all your grades and send it over Telegram or any other of the communication channels listed in the app!

**For Windows users**: Windows Defender may still warn on the unsigned PyInstaller build. If the download is blocked, allow/restore that official release file, or run `python scripts/course_glob_ui.py` from a clone instead (see developer steps below).

**For Linux users**: the app may not be executable initially when you download it. You can fix it by running `chmod +x <file_path>`. Alternatively, you can create this script `install_grades.sh`:

```
bash
#!/usr/bin/bash

wget "https://github.com/mykolamor/tum_info/releases/latest/download/Grades"
chmod +x ./Grades
```

And then run it using `bash install_grades.sh`.

**For developers**: to build the app, you need to:

1. Install `python>=3.7`
2. Install `BeautifulSoup4 requests PySide6 pyinstaller` through `pip`.
3. You can test-run the app running `python scripts/course_glob_ui.py` from root folder.
4. To build it, run `pyinstaller scripts/course_glob_ui.spec`, the results will be placed in the `dist` folder.
5. To package for MacOS, you need to have an additional utility installed through `brew install create-dmg`. Then run `./scripts/course_glob_ui_build.sh` from root folder.

#### Grade download script

A handy script was created to extract all grade reports for a TUMOnline student account. To run the script:

1. Install git, add it to PATH.
2. Fork the repository, clone your fork.
3. Install Python 3.7 or newer, add python and pip to PATH.
4. Run `pip install requests`.
5. From repository root run `python scripts/course_glob.py name=ab12cde@mytum.de pass=42424242`.
6. If you get errors, report them by creating a new issue.
7. Check endterm/retake filenames and field in files. Check exam_type, mode, lang fields in files.
8. Commit changes, push to your fork, create a pull request.

### API

An official unofficial TUM info API is offered with all of the tabular data from the website.

- [description](https://mykolamor.github.io/tum_info/api/description) is a description of supported API endpoints.
- [playground](https://mykolamor.github.io/tum_info/api/playground) is a page where you can execute your own JS upon the API endpoints.
- [schools.json](https://mykolamor.github.io/tum_info/api/schools.json) has an unordered list of all supported schools and their departments. This data is used later for grouping and sorting the courses per-school and per-department.
- [courses.json](https://mykolamor.github.io/tum_info/api/courses.json) has an unordered list of all course exam statistics from the website, including the plot data. This is then grouped and displayed in the general courses page and per-school.

### Feature requests and bug reports

There also are issue templates for such cases [back on GitHub](https://github.com/mykolamor/tum_info/issues/new/choose).
If something is wrong or you want something to get better, here's what to do:
1. Create a new issue and outline what is wrong and/or what you need.
2. (Optionally) If you want to try and fix the issue, state it in a comment, fork the repo, make the changes, and submit a pull request.

## Building the project yourself

Building instructions for the grade download app are listed above. To build the website, you need to install `jekyll` by following the instructions from the official website.
Afterwards, in the root folder run the following commands:
- `bundle install` to install required packages
- `bundle exec jekyll build` to build the website to the `_site` folder
- `bundle exec jekyll serve` to run the website locally

Scripts in the `scripts` folder:

- `course-create.js` is meant for the GitHub Action to create a course file from a GitHub issue.
- `course_functions.py` is a library used by other scripts for TUMOnline-related requests.
- `course_glob.py` is a command-line utility script to download all grades from a particular student by username and password.
- `course_glob_ui.py` is the main file of the GUI app to download all grades.
- `course_glob_resources.py` is the resource file containing icons for the GUI app.
- `course_glob_import.py` is an import command-line utility script to add grades of other students when they send them via JSON.
- `course_glob_resources.qrc` is a QT resource description file for the GUI icons.
- `course_glob_ui.spec` is a PyInstaller spec file to build single-file executables for the GUI app.
- `course_glob_ui_build.sh` is a MacOS script to generate an installer package for the GUI app.
- `course_html_parse.py` is a deprecated command-line utility script to download grades from an outdated website.
- `course_offered_parse.py` is a command-line utility script to download offered courses from a vendor repository.
