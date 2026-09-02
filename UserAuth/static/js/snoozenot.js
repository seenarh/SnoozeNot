function getCsrfToken() {
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return cookie ? cookie.split('=')[1] : '';
}

function toggleTask(taskId) {
  fetch(`/accounts/toggle-task/${taskId}/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({}),
  })
    .then(res => res.json())
    .then(data => { if (data.ok) location.reload(); });
}

function deleteTask(taskId) {
  if (!confirm('Delete this task?')) return;
  fetch(`/accounts/delete_task/${taskId}/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
    .then(res => res.json())
    .then(data => { if (data.ok) location.reload(); });
}

function initSidebar() {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!toggle || !sidebar) return;

  function close() {
    sidebar.classList.remove('open');
    overlay?.classList.remove('open');
  }

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    overlay?.classList.toggle('open');
  });
  overlay?.addEventListener('click', close);
}

const ALARM_DISMISS_KEY = 'snoozenot_dismissed_alarms';
const ALARM_MAX_OVERDUE_MS = 15 * 60 * 1000;
const ALARM_SCHEDULE_LIMIT_MS = 24 * 60 * 60 * 1000;

let alarmQueue = [];
let activeAlarm = null;
let alarmAudioCtx = null;
let alarmRinging = false;
let alarmRingTimer = null;
let alarmAudioUnlocked = false;

function dismissedAlarms() {
  try {
    return new Set(
      JSON.parse(sessionStorage.getItem(ALARM_DISMISS_KEY) || '[]').map(String)
    );
  } catch (err) {
    return new Set();
  }
}

function markAlarmDismissed(id) {
  const dismissed = dismissedAlarms();
  dismissed.add(String(id));
  sessionStorage.setItem(ALARM_DISMISS_KEY, JSON.stringify([...dismissed]));
}

function getAlarmAudio() {
  return document.getElementById('alarm-sound');
}

function setTapHint(visible) {
  const hint = document.getElementById('alarm-tap-hint');
  if (hint) hint.hidden = !visible;
}

function unlockAlarmAudio() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (AudioCtx && !alarmAudioCtx) {
    alarmAudioCtx = new AudioCtx();
  }
  if (alarmAudioCtx && alarmAudioCtx.state === 'suspended') {
    alarmAudioCtx.resume();
  }

  const audio = getAlarmAudio();
  if (!audio || alarmAudioUnlocked || alarmRinging) return;
  audio.muted = true;
  const play = audio.play();
  if (play && play.then) {
    play.then(() => {
      if (!alarmRinging) {
        audio.pause();
        audio.currentTime = 0;
      }
      audio.muted = false;
      alarmAudioUnlocked = true;
    }).catch(() => {
      audio.muted = false;
    });
  }
}

function strikeBell(time) {
  if (!alarmAudioCtx) return;
  const partials = [
    [987.77, 0.22],
    [1480, 0.14],
    [1975.5, 0.1],
    [2480, 0.07],
    [3120, 0.045],
    [890, 0.09],
  ];
  partials.forEach(([freq, amp]) => {
    const osc = alarmAudioCtx.createOscillator();
    const gain = alarmAudioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, time);
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(amp, time + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.55);
    osc.connect(gain);
    gain.connect(alarmAudioCtx.destination);
    osc.start(time);
    osc.stop(time + 0.56);
  });
}

function startWebAudioRing() {
  if (!alarmAudioCtx || !alarmRinging) return;
  if (alarmAudioCtx.state === 'suspended') {
    alarmAudioCtx.resume();
  }
  const ringCycle = () => {
    if (!alarmRinging || !alarmAudioCtx) return;
    const now = alarmAudioCtx.currentTime;
    strikeBell(now);
    strikeBell(now + 0.44);
    alarmRingTimer = window.setTimeout(ringCycle, 1850);
  };
  ringCycle();
}

function startAlarmRing() {
  stopAlarmRing();
  alarmRinging = true;
  setTapHint(false);
  unlockAlarmAudio();

  const audio = getAlarmAudio();
  if (audio) {
    audio.loop = true;
    audio.volume = 1;
    audio.currentTime = 0;
    const play = audio.play();
    if (play && play.then) {
      play.then(() => {
        alarmAudioUnlocked = true;
        setTapHint(false);
      }).catch(() => {
        startWebAudioRing();
        setTapHint(true);
      });
      return;
    }
  }
  startWebAudioRing();
}

function stopAlarmRing() {
  alarmRinging = false;
  if (alarmRingTimer) {
    window.clearTimeout(alarmRingTimer);
    alarmRingTimer = null;
  }
  const audio = getAlarmAudio();
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }
  setTapHint(false);
}

function showBrowserNotification(alarm) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    new Notification(`SnoozeNot — ${alarm.title}`, {
      body: alarm.display || 'Your web alarm is ringing.',
      tag: `snoozenot-alarm-${alarm.id}`,
    });
  } catch (err) {
    /* Notifications can fail in insecure contexts. */
  }
}

function renderAlarm(alarm) {
  const overlay = document.getElementById('alarm-overlay');
  const title = document.getElementById('alarm-title');
  const details = document.getElementById('alarm-details');
  const when = document.getElementById('alarm-when');
  const kicker = overlay && overlay.querySelector('.alarm-kicker');
  if (!overlay || !title) return;

  activeAlarm = alarm;
  title.textContent = alarm.title || 'Task reminder';
  if (kicker) kicker.textContent = alarm.label || 'Alarm ringing';
  if (details) {
    details.textContent = alarm.details || '';
    details.hidden = !alarm.details;
  }
  if (when) when.textContent = alarm.display || '';
  overlay.classList.add('open');
  startAlarmRing();
  showBrowserNotification(alarm);
}

function fireAlarm(alarm) {
  if (dismissedAlarms().has(String(alarm.id))) return;
  if (activeAlarm) {
    if (!alarmQueue.some((item) => item.id === alarm.id)) {
      alarmQueue.push(alarm);
    }
    return;
  }
  renderAlarm(alarm);
}

function dismissAlarm() {
  stopAlarmRing();
  if (activeAlarm) {
    markAlarmDismissed(activeAlarm.id);
  }
  activeAlarm = null;
  const next = alarmQueue.shift();
  if (next) {
    renderAlarm(next);
    return;
  }
  const overlay = document.getElementById('alarm-overlay');
  if (overlay) {
    overlay.classList.remove('open');
  }
}

function scheduleWebAlarms(alarms) {
  const dismissed = dismissedAlarms();
  const now = Date.now();

  alarms.forEach((alarm) => {
    if (dismissed.has(String(alarm.id))) return;
    const when = new Date(alarm.alarm).getTime();
    if (Number.isNaN(when)) return;
    const delay = when - now;
    if (delay > ALARM_SCHEDULE_LIMIT_MS) return;
    if (delay > 0) {
      window.setTimeout(() => fireAlarm(alarm), delay);
    } else if (-delay <= ALARM_MAX_OVERDUE_MS) {
      fireAlarm(alarm);
    }
  });
}

function initWebAlarms() {
  const dataEl = document.getElementById('web-alarms-data');
  const overlay = document.getElementById('alarm-overlay');
  if (!dataEl || !overlay) return;

  let alarms = [];
  try {
    alarms = JSON.parse(dataEl.textContent);
  } catch (err) {
    return;
  }

  ['pointerdown', 'keydown', 'touchstart'].forEach((eventName) => {
    document.addEventListener(eventName, unlockAlarmAudio, { once: true });
  });
  document.getElementById('alarm-dismiss')?.addEventListener('click', dismissAlarm);
  document.getElementById('alarm-complete')?.addEventListener('click', () => {
    const taskId = activeAlarm && (activeAlarm.taskId || activeAlarm.id);
    dismissAlarm();
    if (taskId) toggleTask(taskId);
  });
  overlay.addEventListener('click', (event) => {
    if (!overlay.classList.contains('open')) return;
    if (event.target.closest('.alarm-actions')) return;
    const hint = document.getElementById('alarm-tap-hint');
    if (hint && !hint.hidden) startAlarmRing();
  });

  scheduleWebAlarms(alarms);
}

function initAlarmPermission() {
  if (!('Notification' in window) || Notification.permission !== 'default') return;
  document.querySelectorAll('.form-card form').forEach((form) => {
    form.addEventListener('submit', () => {
      Notification.requestPermission();
    });
  });
}

const FOCUS_DEFAULT_SECONDS = 25 * 60;

function formatFocusClock(totalSeconds) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
}

function initFocusZone() {
  const zone = document.getElementById('focus-zone');
  const clock = document.getElementById('focus-clock');
  const startBtn = document.getElementById('focus-start');
  const pauseBtn = document.getElementById('focus-pause');
  const saveBtn = document.getElementById('focus-end');
  const status = document.getElementById('focus-status');
  const todayEl = document.getElementById('focus-today');
  if (!zone || !clock || !startBtn) return;

  const logUrl = zone.dataset.logUrl;
  const taskId = zone.dataset.taskId || '';
  let remaining = FOCUS_DEFAULT_SECONDS;
  let elapsed = 0;
  let running = false;
  let tick = null;
  let lastStamp = null;
  let saving = false;

  function render() {
    clock.textContent = formatFocusClock(remaining);
    startBtn.textContent = elapsed && !running ? 'Resume' : 'Start';
    startBtn.disabled = running;
    if (pauseBtn) pauseBtn.disabled = !running;
  }

  function stopTick() {
    if (tick) {
      window.clearInterval(tick);
      tick = null;
    }
  }

  function pulse() {
    const now = Date.now();
    const delta = (now - lastStamp) / 1000;
    lastStamp = now;
    remaining -= delta;
    elapsed += delta;
    if (remaining <= 0) {
      remaining = 0;
      running = false;
      stopTick();
      saveFocus();
    }
    render();
  }

  function saveFocus() {
    if (saving) return;
    if (running) pulse();
    running = false;
    stopTick();
    render();
    const minutes = Math.max(0, Math.round(elapsed / 60));
    if (minutes < 1) {
      if (status) status.textContent = 'Sprint needs at least a minute to save.';
      return;
    }
    saving = true;
    fetch(logUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({ minutes, task_id: taskId || null }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && todayEl) todayEl.textContent = data.focus_label;
        elapsed = 0;
        remaining = FOCUS_DEFAULT_SECONDS;
        if (status) status.textContent = `Saved ${minutes} min.`;
        render();
      })
      .catch(() => {
        if (status) status.textContent = 'Could not save focus time.';
      })
      .finally(() => {
        saving = false;
      });
  }

  startBtn.addEventListener('click', () => {
    if (running) return;
    running = true;
    lastStamp = Date.now();
    stopTick();
    tick = window.setInterval(pulse, 250);
    if (status) status.textContent = 'Sprint running — stay on this tab.';
    render();
  });
  pauseBtn?.addEventListener('click', () => {
    if (!running) return;
    pulse();
    running = false;
    stopTick();
    if (status) status.textContent = 'Paused.';
    render();
  });
  saveBtn?.addEventListener('click', saveFocus);
  render();
}

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initWebAlarms();
  initAlarmPermission();
  initFocusZone();
});
