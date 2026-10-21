(async function() {
    const scriptTag = document.currentScript;
    const defaultLang = 'en';
    const defaultContainerQuery = 'body';

    function barColor(d)
    {
        const v = d.grade;
        if (v <= 4.0) {
            const hue = (4.0 - v) * 40.0;
            return `hsl(${hue}, 100%, 50%)`;
        }
        else if (v <= 5.0) {
            const hue = (5.0 - v) * 25.0 + 25.0;
            return `hsl(0, 100%, ${hue}%)`;
        }
        else if (v >= 8.0) {
            return 'hsl(0, 100%, 50%)';
        }
        else if (v >= 7.0) {
            return 'hsl(120, 100%, 50%)';
        }
        return 'hsl(0, 0%, 25%)';
    };
        
    function round(x, digits)
    {
      const result = Number.parseFloat(x).toFixed(digits);
      return result.endsWith('0') ? Number.parseFloat(x).toFixed(digits - 1) : result;
    }

    const langMargins = {
      'de': {
        marginLeft: 205.0
      },
      'en': {
        marginLeft: 175.0
      },
      'none': {
        marginLeft: 35.0
      },
    };

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    try {
        const courseApiModule = await import('https://mykolamor.github.io/tum_info/assets/js/course-api.mjs');
        await loadScript(`${courseApiModule.courseBaseUrl}/assets/js/d3@7.js`);
        await loadScript(`${courseApiModule.courseBaseUrl}/assets/js/plot@0.6.js`);
    
        const widgetContainer = document.createElement('div');
        widgetContainer.id = 'course-plot';
        
        // Replace the script tag with the widget
        const courseCode = scriptTag.dataset.course;
        const courseSemester = scriptTag.dataset.semester;
        const containerQuery = scriptTag.dataset.containerQuery ?? defaultContainerQuery;
        scriptTag.parentNode.replaceChild(widgetContainer, scriptTag);
    
        const courseMatches = await courseApiModule.fetchCourse(courseCode, courseSemester);
        if (courseMatches.length < 1) {
            throw new Error('Failed to fetch a course that matches data parameters.');
        }

        const grades = courseMatches[0].grades.map(x => Object({'grade':x.grade,'people':x.people,'text':null}));

        const lang = localStorage.getItem('lang') ?? defaultLang;
        const langMapping = courseApiModule.courseLangMappings[lang];
        const langLabels = langMapping.labels;

        function getGradeLabel(grade) {
          for (let key of langLabels) {
            if (grade >= key.grade) {
              if (grade > 6.0) {
                return key.text;
              }
        
              const gradeVal = grade > 5.0 ? 5.0 : grade;
              return `${gradeVal.toFixed(1)}${key.text}`;
            }
          }
        };

        grades.forEach((element) => {
          element.text = getGradeLabel(element.grade);
        });

        const attempts = grades.filter(x => x.grade < 6.0);
        const gradesDisplay = localStorage.getItem('course-plot-absent') === 'false' ? attempts : grades;
        const attemptsTotalGlobal = grades.filter(x => x.grade !== 6.0).reduce((partialSum, a) => partialSum + a.people, 0);
        
        const attemptsTotalGlobalSafe = attemptsTotalGlobal === 0 ? 1 : attemptsTotalGlobal;
        const wrapper = document.querySelector(containerQuery);
        const wrapperStyle = getComputedStyle(wrapper);
        const plotWidth = parseInt(wrapperStyle['width']);
        const plotHeight = Math.round(36.6 * (gradesDisplay.length + 1));
        const plotMarginRight = 60.0;
        const plotMarginLeft = langMargins[lang].marginLeft;

        function getGradePlotLegend(d) {
          const div = Math.min(d.people / attemptsTotalGlobalSafe, 1.0);
          const parts = round(div * 100.0, 2);
          return `${parts}% #${d.people}`;
        }
    
        const plot = Plot.plot({
            marks: [
              Plot.barX(gradesDisplay, {x: 'people', y: 'text', fill: barColor}),
              Plot.text(gradesDisplay, {
                x: 'people',
                y: 'text',
                text: getGradePlotLegend,
                fill: 'var(--minima-text-color)',
                dx: plotMarginRight / 2.0})
            ],
            height: plotHeight,
            width: plotWidth,
            marginRight: plotMarginRight,
            marginLeft: plotMarginLeft,
            y: { type: "band", label: langMapping.yLabel, line: true },
            x: { label: langMapping.xLabel, grid: true }
          });
          
          plot.style.backgroundColor = 'transparent';
          widgetContainer.append(plot);
    }
    catch (error) {
        console.error('Error rendering course data:', error);
    }
})();