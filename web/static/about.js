// About page: what the converter changes, privacy, how the browser version relates to the Python, how to run it, credits.
import { route, app, api, isStatic, esc, list } from './core.js';

route('about', async () => {
  const info = await api('/info');
  app().innerHTML = `<p class="kicker">About</p><h1>Strava TCX to Garmin</h1>
    <p class="lead">${esc(info.description)}</p>
    <h2>What the conversion changes</h2>
    <p>The script rebuilds each file in the structure of TCX files that Garmin Connect accepts. With <code>-v</code> the
      command-line script prints the same list:</p>
    <ul>${list(info.changes, c => `<li>${esc(c)}</li>`)}</ul>
    <p>Activities without GPS get the placeholder position ${info.default_lat}, ${info.default_lng}
      (${esc(info.default_place)}, changeable) and altitude ${esc(info.default_altitude)} m on every trackpoint. Lap
      extensions, where a lap has them, are rewritten with the fixed average speed ${esc(info.default_avg_speed)} m/s. Where a trackpoint has
      power but no recorded speed, speed is estimated as max(0.1, watts / 50) m/s, a rough figure.</p>
    <h2>Workflow for Peloton users</h2>
    <ol><li>Export your workouts from Strava as TCX files.</li><li>Convert them here (or with the script).</li>
      <li>Import the <code>_garmin.tcx</code> files in Garmin Connect.</li></ol>
    <p class="small mute">If Garmin Connect still rejects a file, the README suggests converting the converted TCX to FIT
      with the GOTOES tool (<a href="https://gotoes.org/strava/Combine_GPX_TCX_FIT_Files.php">gotoes.org</a>).</p>
    <h2>Privacy</h2>
    <p>${isStatic()
      ? 'This site is static: there is no server that could receive your files. They are read and converted by JavaScript in your browser tab and the results are saved straight to your device.'
      : 'In this local app the conversion also runs in the browser; "Check with the Python converter" sends the files only to the Python server running on this computer, which converts them in memory and stores nothing.'}</p>
    <h2>Browser version vs Python</h2>
    <p>The conversion in <code>tcx_core.py</code> was ported to JavaScript, including the Python behaviours it relies on
      (ElementTree parsing, indentation and escaping, <code>datetime.fromisoformat</code>, <code>float()</code> and how
      Python prints floats). A node test converts the synthetic sample files in <code>tests/fixtures</code> and requires
      output byte-identical to the Python's; a seeded fuzz test compares both on thousands of mutated files.
      ${isStatic() ? '' : 'Here you can also check any of your own files: "Check with the Python converter" compares the two outputs byte for byte.'}</p>
    <h2>Run it yourself</h2>
    <pre>git clone https://github.com/gddickinson/convert_strava_tcx_to_garmin
cd convert_strava_tcx_to_garmin
python tcx_converter.py ride.tcx                 # -> ride_garmin.tcx (standard library only)
python tcx_converter.py ~/Downloads/strava/ -o ~/Desktop/garmin_ready/ -v   # a whole folder

pip install -r requirements-web.txt
python run_web.py                                # web app at http://127.0.0.1:8153</pre>
    <h2>Credits</h2>
    <p>By George Dickinson (<a href="https://github.com/gddickinson/convert_strava_tcx_to_garmin">gddickinson/convert_strava_tcx_to_garmin</a>),
      MIT licence. Built with AI assistance from Claude (Anthropic). Not affiliated with Strava or Garmin. The sample
      files are synthetic (invented times, values and coordinates).</p>`;
});
