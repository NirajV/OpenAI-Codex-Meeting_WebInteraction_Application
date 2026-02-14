const teamForm = document.getElementById('teamForm');
const memberForm = document.getElementById('memberForm');
const meetingForm = document.getElementById('meetingForm');
const teamList = document.getElementById('teamList');
const memberList = document.getElementById('memberList');
const meetingList = document.getElementById('meetingList');
const memberTeams = document.getElementById('memberTeams');
const inviteeCheckboxes = document.getElementById('inviteeCheckboxes');
const message = document.getElementById('message');
const scheduleType = document.getElementById('scheduleType');
const recurringFields = document.getElementById('recurringFields');

const showMessage = (text, isError = false) => {
  message.textContent = text;
  message.style.color = isError ? '#b91c1c' : '#047857';
};

const fetchJSON = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Request failed');
  }

  return data;
};

const refreshTeams = async () => {
  const teams = await fetchJSON('/api/teams');
  teamList.innerHTML = teams.map((team) => `<li>${team.name}</li>`).join('');

  memberTeams.innerHTML = teams
    .map((team) => `<option value="${team.id}">${team.name}</option>`)
    .join('');
};

const refreshMembers = async () => {
  const members = await fetchJSON('/api/members');
  memberList.innerHTML = members
    .map((member) => `<li>${member.fullName} (${member.email}) - Teams: ${member.teams || 'None'}</li>`)
    .join('');

  inviteeCheckboxes.innerHTML = members
    .map(
      (member) =>
        `<label><input type="checkbox" value="${member.id}" /> ${member.fullName} (${member.email})</label>`
    )
    .join('');
};

const refreshMeetings = async () => {
  const meetings = await fetchJSON('/api/meetings');
  meetingList.innerHTML = meetings
    .map(
      (meeting) =>
        `<li><strong>${meeting.name}</strong> - ${meeting.scheduleType} at ${meeting.startsAt}` +
        `${meeting.startTime && meeting.endTime ? ` (${meeting.startTime} - ${meeting.endTime})` : ''} (${meeting.timezone})` +
        `${meeting.recurrenceRule ? ` | Rule: ${meeting.recurrenceRule}` : ''}` +
        `${meeting.recurrenceEndDate ? ` | Ends: ${meeting.recurrenceEndDate}` : ''}` +
        `<br/>Invitees: ${meeting.invitees || 'None'}</li>`
    )
    .join('');
};

teamForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await fetchJSON('/api/teams', {
      method: 'POST',
      body: JSON.stringify({ name: document.getElementById('teamName').value }),
    });
    teamForm.reset();
    await refreshTeams();
    showMessage('Team created successfully.');
  } catch (error) {
    showMessage(error.message, true);
  }
});

memberForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const selectedTeamIds = [...memberTeams.selectedOptions].map((option) => Number(option.value));

  try {
    await fetchJSON('/api/members', {
      method: 'POST',
      body: JSON.stringify({
        fullName: document.getElementById('memberName').value,
        email: document.getElementById('memberEmail').value,
        teamIds: selectedTeamIds,
      }),
    });
    memberForm.reset();
    await refreshMembers();
    showMessage('Member added successfully.');
  } catch (error) {
    showMessage(error.message, true);
  }
});

meetingForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const inviteeIds = [...inviteeCheckboxes.querySelectorAll('input:checked')].map((checkbox) =>
    Number(checkbox.value)
  );

  const payload = {
    name: document.getElementById('meetingName').value,
    startsAt: document.getElementById('startsAt').value,
    startTime: document.getElementById('startTime').value,
    endTime: document.getElementById('endTime').value,
    timezone: document.getElementById('timezone').value,
    scheduleType: scheduleType.value,
    recurrenceRule: document.getElementById('recurrenceRule').value || null,
    recurrenceEndDate: document.getElementById('recurrenceEndDate').value || null,
    inviteeIds,
  };

  try {
    await fetchJSON('/api/meetings', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    meetingForm.reset();
    recurringFields.classList.add('hidden');
    await refreshMeetings();
    showMessage('Meeting created successfully.');
  } catch (error) {
    showMessage(error.message, true);
  }
});

scheduleType.addEventListener('change', () => {
  if (scheduleType.value === 'recurring') {
    recurringFields.classList.remove('hidden');
  } else {
    recurringFields.classList.add('hidden');
  }
});

const init = async () => {
  try {
    await Promise.all([refreshTeams(), refreshMembers(), refreshMeetings()]);
  } catch (error) {
    showMessage(error.message, true);
  }
};

init();
