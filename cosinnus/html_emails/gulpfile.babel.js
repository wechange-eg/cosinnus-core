import gulp     from 'gulp';
import plugins  from 'gulp-load-plugins';
import browser  from 'browser-sync';
import rimraf   from 'rimraf';
import panini   from 'panini';
import yargs    from 'yargs';
import lazypipe from 'lazypipe';
import inky     from 'inky';
import fs       from 'fs';
import siphon   from 'siphon-media-query';
import path     from 'path';
import merge    from 'merge-stream';
import beep     from 'beepbeep';
import colors   from 'colors';

const $ = plugins();

// Look for the --production flag
const PRODUCTION = !!(yargs.argv.production);

var replace = require('gulp-replace');

// Build the "dist" folder by running all of the above tasks
gulp.task('build',
  gulp.series(clean, pages, sass, images, inline, cellspaceClasses));

// Build emails, run the server, and watch for file changes
gulp.task('default',
  gulp.series('build'));
  
// Build emails, run the server, and watch for file changes
gulp.task('dev',
  gulp.series('build', exportTemplates, server, watch));

// Build emails, then zip
gulp.task('zip',
  gulp.series('build', zip));

// Delete the "dist" folder
// This happens every time a build starts
function clean(done) {
  rimraf('dist', done);
}

// Compile layouts, pages, and partials into flat HTML files
// Then parse using Inky templates
function pages() {
  return gulp.src('src/pages/**/*.html')
    .pipe(panini({
      root: 'src/pages',
      layouts: 'src/layouts',
      partials: 'src/partials',
      helpers: 'src/helpers'
    }))
    .pipe(inky())
    .pipe(gulp.dest('dist'));
}

// Reset Panini's cache of layouts and partials
function resetPages(done) {
  panini.refresh();
  done();
}

// Compile Sass into CSS
function sass() {
  return gulp.src('src/assets/scss/app.scss')
    .pipe($.if(!PRODUCTION, $.sourcemaps.init()))
    .pipe($.sass({
      includePaths: ['node_modules/foundation-emails/scss']
    }).on('error', $.sass.logError))
    .pipe($.if(!PRODUCTION, $.sourcemaps.write()))
    .pipe(gulp.dest('dist/css'));
}

// Copy and compress images
function images() {
  return gulp.src('src/assets/img/**/*')
    .pipe($.imagemin())
    .pipe(gulp.dest('./dist/assets/img'));
}

// Inline CSS and minify HTML
function inline() {
  return gulp.src('dist/**/*.html')
    .pipe(inliner('dist/css/app.css'))
    .pipe(gulp.dest('dist'));
}


// add cellspacing/cellpadding onto tables that have padding classes to support Outlook
function cellspaceClasses() {
  return gulp.src('dist/**/*.html')
    .pipe(replace('padding-top: invalid !important;', ''))
    .pipe(replace('padding-right: invalid !important;', ''))
    .pipe(replace('padding-bottom: invalid !important;', ''))
    .pipe(replace('padding-left: invalid !important;', ''))
    
    .pipe(replace(/\s+</gim, '\n<'))  // remove whitespaces between tags for newlines
    .pipe(replace(/<style>[\s\S]+<\/style>/gim, ''))
    
    // there two lines are used to abuse the inliner to print out the content of a SCSS class inline anywhere into the HTML
    // example usage:     </style><inlinemagicreplacer class="primary-color"></inlinemagicreplacer><style no-scrub="1">
    .pipe(replace(/<\/style><inlinemagicreplacer[\s\S]+?style="/gim, '')) 
    .pipe(replace('"></inlinemagicreplacer><style no-scrub="1">', ''))
    
    .pipe(gulp.dest('dist'));
}

// add cellspacing/cellpadding onto tables that have padding classes to support Outlook
function exportTemplates() {
  return gulp.src([
        'dist/summary_group.html',
        'dist/summary_item.html',
        'dist/notification.html',
        'dist/digest.html'
    ])
    .pipe(gulp.dest('./../templates/cosinnus/html_mail/'));
}

// Start a server with LiveReload to preview the site in
function server(done) {
  browser.init({
    server: 'dist'
  });
  done();
}

// Watch for file changes
function watch() {
  gulp.watch('src/**/*.html').on('change', gulp.series(clean, pages, sass, images, inline, cellspaceClasses, exportTemplates, browser.reload));
  gulp.watch(['../scss/**/*.scss', 'src/assets/scss/**/*.scss']).on('change', gulp.series(clean, pages, sass, images, inline, cellspaceClasses, exportTemplates, browser.reload));
  gulp.watch('src/assets/img/**/*').on('change', gulp.series(images, browser.reload));
}

// Inlines CSS into HTML, adds media query CSS into the <style> tag of the email, and compresses the HTML
function inliner(css) {
  var css = fs.readFileSync(css).toString();
  var mqCss = siphon(css);

  var pipe = lazypipe()
    .pipe($.inlineCss, {
      applyStyleTags: false,
      removeStyleTags: false,
      removeLinkTags: true
    })
    .pipe($.replace, '<!-- <style> -->', `<style>${css}</style>`)
    .pipe($.htmlmin, {
      collapseWhitespace: false,
      minifyCSS: false,
    });

  return pipe();
}

// Copy and compress into Zip
function zip() {
  var dist = 'dist';
  var ext = '.html';

  function getHtmlFiles(dir) {
    return fs.readdirSync(dir)
      .filter(function(file) {
        var fileExt = path.join(dir, file);
        var isHtml = path.extname(fileExt) == ext;
        return fs.statSync(fileExt).isFile() && isHtml;
      });
  }

  var htmlFiles = getHtmlFiles(dist);

  var moveTasks = htmlFiles.map(function(file){
    var sourcePath = path.join(dist, file);
    var fileName = path.basename(sourcePath, ext);

    var moveHTML = gulp.src(sourcePath)
      .pipe($.rename(function (path) {
        path.dirname = fileName;
        return path;
      }));

    var moveImages = gulp.src(sourcePath)
      .pipe($.htmlSrc({ selector: 'img'}))
      .pipe($.rename(function (path) {
        path.dirname = fileName + '/assets/img';
        return path;
      }));

    return merge(moveHTML, moveImages)
      .pipe($.zip(fileName+ '.zip'))
      .pipe(gulp.dest('dist'));
  });

  return merge(moveTasks);
}
