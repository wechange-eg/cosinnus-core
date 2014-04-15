'use strict';

module.exports = function (grunt) {

    // load all grunt tasks
    require('matchdep').filterDev('grunt-*').forEach(grunt.loadNpmTasks);

    var base = 'cosinnus/static/';

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),
        watch: {
            options: {
                livereload: true
            },
            livereload: {
                files: ['**/*.html', '**/*.js']
            },
            sass: {
                files: '**/*.s[ac]ss',
                tasks: ['sass:dev']
            }
        },
        sass: {                              // Task
            dev: {                             // Another target
                options: {                       // Target options
                    style: 'expanded',
                    trace: true
                    /* lineNumbers: true */
                },
                files: {
                    'cosinnus/static/css/cosinnus.css': base + '/sass/cosinnus.scss',
                    'cosinnus/static/css/bootstrap3-cosinnus.css': base + '/sass/vendor/bootstrap/bootstrap.scss',
                    'html-mockups/static/css/cosinnus.css': 'html-mockups/static/sass/cosinnus.scss',
                    'html-mockups/static/css/bootstrap3-cosinnus.css': 'html-mockups/static/sass/vendor/bootstrap/bootstrap.scss'
                }
            }
        },
        browser_sync: {
            dev: {
                bsFiles: {
                    src : [
                        base + 'css/cosinnus.css',
                        'cosinnus/templates/cosinnus/*.html',
                        'html-mockups/static/css/cosinnus.css'
                    ]
                },
                options: {
                    watchTask: true,
                    ghostMode: {
                        clicks: true,
                        scroll: true,
                        links: true,
                        forms: true
                    }
                }
            }
        }
    });

    grunt.registerTask('default', [
        'sass', 'browser_sync', 'watch'
    ]);
};
