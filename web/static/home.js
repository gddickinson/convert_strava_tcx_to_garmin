// Home page: hero, privacy note, counts from the API and links to the pages.
import { route, app, api, isStatic, esc } from './core.js';

route('home', async () => {
  const info = await api('/info');
  app().innerHTML = `<section class="hero"><p class="kicker">Strava export → Garmin Connect import</p>
    <h1 class="glow">Strava TCX to Garmin</h1>
    <p class="lead">${esc(info.description)} Garmin Connect often rejects TCX files exported from Strava with "We don't
      support the file type you tried to import"; this rewrites them in the structure Garmin's own files use.</p>
    <a class="btn" href="#/convert">Convert files</a> <a class="btn alt" href="#/convert?sample=1">Try a sample</a></section>
    <p class="privacy"><b>Private by design.</b> ${isStatic()
      ? 'Your files are read and converted by JavaScript in this browser tab. Nothing is uploaded: this site has no server.'
      : 'Your files are converted in this browser tab; the optional Python check sends them only to the app running on this computer.'}</p>
    <div class="tiles">
      <div class="tile"><b>${info.changes.length}</b><span>format changes for Garmin</span></div>
      <div class="tile"><b>0</b><span>bytes uploaded</span></div>
      <div class="tile"><b>.zip</b><span>one download for many files</span></div>
      <div class="tile"><b>${info.samples}</b><span>synthetic samples to try</span></div></div>
    <div class="grid">
      <a class="card" href="#/convert"><b>Convert</b><small>drop .tcx files</small><span>Preview each activity (route,
        distance, duration, laps), set the placeholder position for indoor workouts, download the converted files.</span></a>
      <a class="card" href="#/about"><b>About</b><small>what changes · run it locally</small><span>The changes made for
        Garmin, the command-line script, the local web app and how the browser version was checked against the Python.</span></a>
    </div>`;
});
