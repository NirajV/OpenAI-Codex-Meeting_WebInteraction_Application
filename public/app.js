const teamForm = document.getElementById('teamForm');
const memberForm = document.getElementById('memberForm');
const patientDetailsForm = document.getElementById('patientDetailsForm');
const meetingForm = document.getElementById('meetingForm');
const teamList = document.getElementById('teamList');
const memberList = document.getElementById('memberList');
const patientDetailsList = document.getElementById('patientDetailsList');
const meetingList = document.getElementById('meetingList');
const memberTeams = document.getElementById('memberTeams');
const inviteeEmail = document.getElementById('inviteeEmail');
const emailSuggestions = document.getElementById('emailSuggestions');
const patientMeetingId = document.getElementById('patientMeetingId');
const patientAttachments = document.getElementById('patientAttachments');
const message = document.getElementById('message');
const scheduleType = document.getElementById('scheduleType');
const recurringFields = document.getElementById('recurringFields');

// Filter elements
const filterMeetingName = document.getElementById('filterMeetingName');
const filterPatientName = document.getElementById('filterPatientName');
const filterMRN = document.getElementById('filterMRN');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

// Store all meetings data
let allMeetings = [];

const showMessage = (text, isError = false) => {
  message.textContent = text;
  message.style.color = isError ? '#b91c1c' : '#047857';
};

const parseInviteeEmails = (raw) => {
  const trimmed = (raw || '').trim();
  if (!trimmed) {
    return { emails: [], invalid: [] };
  }
  const parts = trimmed.split(',').map((part) => part.trim()).filter(Boolean);
  const unique = [];
  const seen = new Set();
  parts.forEach((email) => {
    const normalized = email.toLowerCase();
    if (!seen.has(normalized)) {
      seen.add(normalized);
      unique.push(normalized);
    }
  });
  const invalid = unique.filter((email) => !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email));
  return { emails: unique, invalid };
};

const toBase64 = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      const [, base64Content = ''] = result.split(',');
      resolve(base64Content);
    };
    reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
    reader.readAsDataURL(file);
  });

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
  memberTeams.innerHTML = teams.map((team) => `<option value="${team.id}">${team.name}</option>`).join('');
};

const refreshMembers = async () => {
  const members = await fetchJSON('/api/members');
  memberList.innerHTML = members
    .map((member) => `<li>${member.fullName} (${member.email}) - Teams: ${member.teams || 'None'}</li>`)
    .join('');
};

const refreshMeetings = async () => {
  const meetings = await fetchJSON('/api/meetings');
  allMeetings = meetings;
  renderMeetings(meetings);

  // Populate email suggestions from all unique invitee emails
  const uniqueEmails = new Set();
  meetings.forEach((meeting) => {
    if (meeting.invitees) {
      // Extract emails from invitees string
      const emailMatches = meeting.invitees.match(/[\w.-]+@[\w.-]+\.\w+/g);
      if (emailMatches) {
        emailMatches.forEach(email => uniqueEmails.add(email));
      }
    }
  });
  emailSuggestions.innerHTML = Array.from(uniqueEmails)
    .map((email) => `<option value="${email}">`)
    .join('');

  patientMeetingId.innerHTML =
    '<option value="">Select meeting</option>' +
    meetings.map((meeting) => `<option value="${meeting.id}">#${meeting.id} - ${meeting.name}</option>`).join('');
};

const renderMeetings = (meetings, nameFilter = '', patientFilter = '', mrnFilter = '') => {
  meetingList.innerHTML = meetings
    .map(
      (meeting) => {
        // If filters are applied, show only matching patients
        let patientsToShow = meeting.patients || [];
        
        if (patientFilter || mrnFilter) {
          patientsToShow = patientsToShow.filter((patient) => {
            const patientNameMatch = !patientFilter || patient.patientName.toLowerCase().includes(patientFilter.toLowerCase());
            const mrnMatch = !mrnFilter || patient.medicalRecordNumber.toLowerCase().includes(mrnFilter.toLowerCase());
            return patientNameMatch && mrnMatch;
          });
        }

        const patientsHtml = patientsToShow && patientsToShow.length > 0
          ? patientsToShow
              .map(
                (p) =>
                  `<br/>&nbsp;&nbsp;<i class="fas fa-user-injured"></i> ${p.patientName} (MRN: ${p.medicalRecordNumber}) | Dr. ${p.doctorName} | ${p.departmentName}`
              )
              .join('')
          : '<br/>&nbsp;&nbsp;<i class="fas fa-exclamation-circle"></i> No patients added yet';
        
        // Format response status
        let responseHtml = '';
        if (meeting.responses && Object.keys(meeting.responses).length > 0) {
          const responses = meeting.responses;
          const counts = {
            pending: 0,
            accepted: 0,
            declined: 0,
            tentative: 0
          };
          
          Object.values(responses).forEach(status => {
            counts[status]++;
          });
          
          responseHtml = `<br/><strong>RSVP Status:</strong> `;
          if (counts.accepted > 0) responseHtml += `<span style="color: green;">✓ ${counts.accepted} Accepted</span> `;
          if (counts.tentative > 0) responseHtml += `<span style="color: orange;">? ${counts.tentative} Tentative</span> `;
          if (counts.declined > 0) responseHtml += `<span style="color: red;">✕ ${counts.declined} Declined</span> `;
          if (counts.pending > 0) responseHtml += `<span style="color: gray;">⟳ ${counts.pending} Pending</span>`;
          
          responseHtml += '<br/>Details: ';
          Object.entries(responses).forEach(([email, status]) => {
            const statusIcon = status === 'accepted' ? '✓' : status === 'declined' ? '✕' : status === 'tentative' ? '?' : '⟳';
            const statusColor = status === 'accepted' ? 'green' : status === 'declined' ? 'red' : status === 'tentative' ? 'orange' : 'gray';
            responseHtml += `<span style="color: ${statusColor};">${statusIcon} ${email} (${status})</span> &nbsp;`;
          });
        }
        
        return (
          `<li><strong>#${meeting.id} ${meeting.name}</strong> - ${meeting.scheduleType} at ${meeting.startsAt}` +
          `${meeting.startTime && meeting.endTime ? ` (${meeting.startTime} - ${meeting.endTime})` : ''} (${meeting.timezone})` +
          `${meeting.recurrenceRule ? ` | Rule: ${meeting.recurrenceRule}` : ''}` +
          `${meeting.recurrenceEndDate ? ` | Ends: ${meeting.recurrenceEndDate}` : ''}` +
          `<br/>Attachments: ${meeting.attachmentCount || 0}${meeting.attachmentNames ? ` (${meeting.attachmentNames})` : ''}` +
          `<br/>Invitees: ${meeting.invitees || 'None'}` +
          `${responseHtml}` +
          `<br/><strong>Patients:</strong>${patientsHtml}</li>`
        );
      }
    )
    .join('');
};

const applyMeetingFilters = () => {
  const nameFilter = filterMeetingName.value.toLowerCase().trim();
  const patientFilter = filterPatientName.value.toLowerCase().trim();
  const mrnFilter = filterMRN.value.toLowerCase().trim();

  const filtered = allMeetings.filter((meeting) => {
    // Filter by meeting name
    if (nameFilter && !meeting.name.toLowerCase().includes(nameFilter)) {
      return false;
    }

    // Filter by patient name and/or MRN (if no patients match, exclude this meeting)
    if (patientFilter || mrnFilter) {
      const hasMatchingPatient = meeting.patients && meeting.patients.some((patient) => {
        const patientNameMatch = !patientFilter || patient.patientName.toLowerCase().includes(patientFilter);
        const mrnMatch = !mrnFilter || patient.medicalRecordNumber.toLowerCase().includes(mrnFilter);
        return patientNameMatch && mrnMatch;
      });

      if (!hasMatchingPatient) {
        return false;
      }
    }

    return true;
  });

  renderMeetings(filtered, nameFilter, patientFilter, mrnFilter);
};

const refreshPatientDetails = async () => {
  const details = await fetchJSON('/api/patient-details');

  patientDetailsList.innerHTML = details
    .map(
      (detail) =>
        `<li><strong>${detail.patientName}</strong> (MRN: ${detail.medicalRecordNumber}, DOB: ${detail.patientDateOfBirth})` +
        `<br/>Meeting: ${detail.meetingId ? `#${detail.meetingId} ${detail.meetingName}` : 'Unassigned'}` +
        `<br/>Doctor: ${detail.doctorName} | Department: ${detail.departmentName}` +
        `${detail.meetingAgendaNote ? `<br/>Agenda: ${detail.meetingAgendaNote}` : ''}` +
        `${detail.patientDescription ? `<br/>Patient Description: ${detail.patientDescription}` : ''}</li>`
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
  const emailInput = inviteeEmail.value;
  const { emails, invalid } = parseInviteeEmails(emailInput);
  if (invalid.length > 0) {
    showMessage(`Invalid email(s): ${invalid.join(', ')}`, true);
    return;
  }

  try {
    const payload = {
      name: document.getElementById('meetingName').value,
      startsAt: document.getElementById('startsAt').value,
      startTime: document.getElementById('startTime').value,
      endTime: document.getElementById('endTime').value,
      timezone: document.getElementById('timezone').value,
      scheduleType: scheduleType.value,
      recurrenceRule: document.getElementById('recurrenceRule').value || null,
      recurrenceEndDate: document.getElementById('recurrenceEndDate').value || null,
      inviteeEmail: emails.length > 0 ? emails.join(', ') : null,
    };

    await fetchJSON('/api/meetings', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    meetingForm.reset();
    recurringFields.classList.add('hidden');
    await Promise.all([refreshMeetings(), refreshPatientDetails()]);
    showMessage('Meeting created successfully.');
  } catch (error) {
    showMessage(error.message, true);
  }
});

patientDetailsForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  try {
    const meetingIdValue = patientMeetingId.value ? Number(patientMeetingId.value) : null;
    
    if (!meetingIdValue) {
      showMessage('Please select a meeting.', true);
      return;
    }

    const attachmentFiles = [...patientAttachments.files];
    const attachments = await Promise.all(
      attachmentFiles.map(async (file) => ({
        fileName: file.name,
        fileType: file.type || null,
        fileData: await toBase64(file),
      }))
    );

    await fetchJSON('/api/patient-details', {
      method: 'POST',
      body: JSON.stringify({
        meetingId: meetingIdValue,
        medicalRecordNumber: document.getElementById('medicalRecordNumber').value,
        patientName: document.getElementById('patientName').value,
        patientDateOfBirth: document.getElementById('patientDateOfBirth').value,
        patientDescription: document.getElementById('patientDescription').value || null,
        doctorName: document.getElementById('doctorName').value,
        departmentName: document.getElementById('departmentName').value,
        meetingAgendaNote: document.getElementById('meetingAgendaNote').value || null,
        attachments,
      }),
    });

    patientDetailsForm.reset();
    await Promise.all([refreshPatientDetails(), refreshMeetings()]);
    showMessage('Patient added to meeting successfully!');
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

// Filter event listeners
filterMeetingName.addEventListener('input', applyMeetingFilters);
filterPatientName.addEventListener('input', applyMeetingFilters);
filterMRN.addEventListener('input', applyMeetingFilters);

clearFiltersBtn.addEventListener('click', () => {
  filterMeetingName.value = '';
  filterPatientName.value = '';
  filterMRN.value = '';
  renderMeetings(allMeetings);
});

const init = async () => {
  try {
    await refreshTeams();
    await refreshMembers();
    await refreshMeetings();
    await refreshPatientDetails();
  } catch (error) {
    showMessage(error.message, true);
  }
};

init();
