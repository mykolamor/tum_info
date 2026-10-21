const courseBaseUrl = 'https://mykolamor.github.io/tum_info';
const courseApiUrl = `${courseBaseUrl}/api/courses.json`;

const courseLangMappings = {
  'de': {
    yLabel: 'note',
    xLabel: 'leute',
    labels: [
      { grade: 8.0, text: ' N fail' },
      { grade: 7.0, text: ' B pass' },
      { grade: 6.0, text: ' × Nicht erschienen - nicht ausreichend' },
      { grade: 4.1, text: ' nicht ausreichend' },
      { grade: 3.4, text: ' ausreichend' },
      { grade: 2.4, text: ' befriedigend' },
      { grade: 1.4, text: ' gut' },
      { grade: 0.0, text: ' sehr gut' },
    ]
  },
  'en': {
    yLabel: 'grade',
    xLabel: 'people',
    labels: [
      { grade: 8.0, text: ' N fail' },
      { grade: 7.0, text: ' B pass' },
      { grade: 6.0, text: ' × Didn\'t show up - not sufficient' },
      { grade: 4.1, text: ' not sufficient' },
      { grade: 3.4, text: ' sufficient' },
      { grade: 2.4, text: ' satisfactory' },
      { grade: 1.4, text: ' good' },
      { grade: 0.0, text: ' very good' },
    ]
  },
  'none': {
    yLabel: 'grade',
    xLabel: 'people',
    labels: [
      { grade: 8.0, text: 'N' },
      { grade: 7.0, text: 'B' },
      { grade: 6.0, text: ' ×' },
      { grade: 4.1, text: '' },
      { grade: 3.4, text: '' },
      { grade: 2.4, text: '' },
      { grade: 1.4, text: '' },
      { grade: 0.0, text: '' },
    ]
  },
};

class Grade {
    constructor(data) {
        this.grade = data.grade;
        this.people = data.people;
    }

    /**
     * Grade value or encoding.
     * @type {number}
     * 
     * @example
     * Grades 1.0-5.0 are mapped as-is.
     * Grade 6.0 means the student did not show up (X).
     * Grade 7.0 means the student passed without a grade (B).
     * Grade 8.0 means the student failed without a grade (N).
     * As of now there is no encoding for (Q).
     */
    grade;
    /**
     * Number of people who got this grade.
     * @type {number}
     */
    people;
}

class Course {
    constructor(data) {
        this.school = data.school;
        this.code = data.code;
        this.semester = data.semester;
        this.examType = data.examType;
        this.name = data.name;
        this.date = new Date(data.date);
        this.ects = data.ects;
        this.hours = data.hours;
        this.mode = data.mode;
        this.lang = data.lang;
        this.peopleTotal = data.peopleTotal;
        this.peopleFailed = data.peopleFailed;
        this.attemptsTotal = data.attemptsTotal;
        this.attemptsFailedPercent = data.attemptsFailedPercent;
        this.averageTotal = data.averageTotal;
        this.averagePassed = data.averagePassed;
        this.grades = data.grades.map(grade => new Grade(grade));
    }

    school;
    code;
    semester;
    examType;
    name;
    date;
    ects;
    hours;
    mode;
    lang;
    peopleTotal;
    peopleFailed;
    attemptsTotal;
    attemptsFailedPercent;
    averageTotal;
    averagePassed;
    /**
     * One or more grade statistics for a course.
     * @type {Array<Grade>}
     */
    grades;

    /**
     * List of available courses.
     * @type {Array<Course> | undefined}
     */
    static courseList = undefined;
}

/**
 * 
 * @param {string} code uppercase course code, e.g., IN2386.
 * @param {string | undefined} semester uppercase semester of course start, e.g., 2023WS or 23WS.
 * @param {string | undefined} apiUrl URL to fetch course data from. Defaults to statically hosted website.
 * 
 * @returns {Promise<Array<Course>>} Zero or more courses that match the code and optionally semester.
 */
async function fetchCourse(code, semester, apiUrl) {
    if (apiUrl === undefined) {
        apiUrl = courseApiUrl;
    }

    if (Course.courseList === undefined) {
        try {
            const response = await fetch(apiUrl);
            Course.courseList = await response.json();
        }
        catch (error) {
            console.error('Error fetching course data:', error);
        }
    }

    if (Course.courseList !== undefined) {
        if (semester !== undefined) {
            if (semester.length === 4) semester = '20' + semester;
            return Course.courseList.filter(x => x.semester === semester && x.code === code);
        } else {
            return Course.courseList.filter(x => x.code === code);
        }
    }

    return [];
}

export {
    courseBaseUrl,
    courseApiUrl,
    courseLangMappings,
    Grade,
    Course,
    fetchCourse,
};