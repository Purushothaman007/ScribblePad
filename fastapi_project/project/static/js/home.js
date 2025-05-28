document.addEventListener('DOMContentLoaded', () => {
    // Popup toggle for adding notes
    const addNoteButton = document.getElementById('add-note');
    const popupOverlay = document.getElementById('popup-overlay');
    const popupBox = document.getElementById('popup-box');
    const closePopupButton = document.getElementById('close-popup');

    if (addNoteButton && popupOverlay && popupBox) {
        addNoteButton.addEventListener('click', () => {
            popupOverlay.style.display = 'block';
            popupBox.style.display = 'block';
        });
    }

    if (closePopupButton) {
        closePopupButton.addEventListener('click', () => {
            popupOverlay.style.display = 'none';
            popupBox.style.display = 'none';
            const noteForm = document.getElementById('note-form');
            const reminderToggle = document.getElementById('set-reminder');
            const reminderDateInput = document.getElementById('reminder-date');
            const setReminderHidden = document.getElementById('set-reminder-hidden');
            const tagSelect = document.getElementById('tag-new');
            
            if (noteForm) {
                noteForm.reset();
            }
            if (reminderToggle && reminderDateInput && setReminderHidden) {
                reminderToggle.setAttribute('data-state', 'off');
                reminderToggle.textContent = 'Off';
                setReminderHidden.value = 'off';
                reminderDateInput.disabled = true;
                reminderDateInput.value = '';
            }
            if (tagSelect) {
                tagSelect.value = '';
            }
        });
    }

    // Toggle edit form for each note
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', () => {
            const noteId = button.getAttribute('data-note-id');
            const editForm = document.getElementById(`edit-form-${noteId}`);
            if (editForm) {
                editForm.style.display = editForm.style.display === 'none' ? 'block' : 'none';
            }
        });
    });

    // Toggle tag form for each note
    document.querySelectorAll('.tag-btn').forEach(button => {
        button.addEventListener('click', () => {
            const noteId = button.getAttribute('data-note-id');
            const tagForm = document.getElementById(`tag-form-${noteId}`);
            if (tagForm) {
                tagForm.style.display = tagForm.style.display === 'none' ? 'block' : 'none';
            }
        });
    });

    // Cancel edit form
    document.querySelectorAll('.cancel-edit').forEach(button => {
        button.addEventListener('click', () => {
            const noteId = button.getAttribute('data-note-id');
            const editForm = document.getElementById(`edit-form-${noteId}`);
            const reminderToggle = document.getElementById(`set-reminder-${noteId}`);
            const reminderDateInput = document.getElementById(`edit-reminder-date-${noteId}`);
            const setReminderHidden = document.getElementById(`set-reminder-hidden-${noteId}`);
            const tagSelect = document.getElementById(`tag-${noteId}`);
            
            // Reset reminder fields to original state
            if (reminderToggle && reminderDateInput && setReminderHidden) {
                const originalState = reminderToggle.getAttribute('data-state');
                reminderToggle.setAttribute('data-state', originalState);
                reminderToggle.textContent = originalState === 'on' ? 'On' : 'Off';
                setReminderHidden.value = originalState;
                reminderDateInput.disabled = originalState !== 'on';
                if (originalState !== 'on') {
                    reminderDateInput.value = '';
                } else {
                    reminderDateInput.value = reminderDateInput.getAttribute('value') || '';
                }
            }
            
            // Reset tag to original state
            if (tagSelect) {
                tagSelect.value = tagSelect.getAttribute('data-original-tag') || '';
            }
            
            if (editForm) {
                editForm.style.display = 'none';
            }
        });
    });

    // Cancel tag form
    document.querySelectorAll('.cancel-tag').forEach(button => {
        button.addEventListener('click', () => {
            const noteId = button.getAttribute('data-note-id');
            const tagForm = document.getElementById(`tag-form-${noteId}`);
            const tagSelect = document.getElementById(`tag-${noteId}`);
            
            // Reset tag to original state
            if (tagSelect) {
                tagSelect.value = tagSelect.getAttribute('data-original-tag') || '';
            }
            
            if (tagForm) {
                tagForm.style.display = 'none';
            }
        });
    });

    // Store original tag for reset
    document.querySelectorAll('select[id^="tag-"]').forEach(select => {
        select.setAttribute('data-original-tag', select.value);
    });

    // Delete confirmation popup logic
    let deleteFormId = null;

    window.showDeleteConfirm = function(formId) {
        deleteFormId = formId; // Store the form ID to submit later
        const deleteOverlay = document.getElementById('delete-overlay');
        const deleteConfirmBox = document.getElementById('delete-confirm-box');
        if (deleteOverlay && deleteConfirmBox) {
            deleteOverlay.style.display = 'block';
            deleteConfirmBox.style.display = 'block';
        }
    };

    window.confirmDelete = function() {
        if (deleteFormId) {
            const form = document.getElementById(deleteFormId);
            if (form) {
                form.submit(); // Submit the form
            }
        }
        hideDeleteConfirm();
    };

    window.cancelDelete = function() {
        hideDeleteConfirm();
    };

    function hideDeleteConfirm() {
        const deleteOverlay = document.getElementById('delete-overlay');
        const deleteConfirmBox = document.getElementById('delete-confirm-box');
        if (deleteOverlay && deleteConfirmBox) {
            deleteOverlay.style.display = 'none';
            deleteConfirmBox.style.display = 'none';
        }
        deleteFormId = null; // Clear the stored form ID
    }

    // Reminder toggle logic for Add Note form
    const setReminderToggle = document.getElementById('set-reminder');
    const reminderDateInput = document.getElementById('reminder-date');
    const setReminderHidden = document.getElementById('set-reminder-hidden');

    if (setReminderToggle && reminderDateInput && setReminderHidden) {
        setReminderToggle.addEventListener('click', () => {
            const currentState = setReminderToggle.getAttribute('data-state');
            const newState = currentState === 'on' ? 'off' : 'on';
            setReminderToggle.setAttribute('data-state', newState);
            setReminderToggle.textContent = newState === 'on' ? 'On' : 'Off';
            setReminderHidden.value = newState;
            reminderDateInput.disabled = newState !== 'on';
            if (newState !== 'on') {
                reminderDateInput.value = '';
            }
        });

        // Prevent past dates
        const today = new Date().toISOString().split('T')[0];
        reminderDateInput.setAttribute('min', today);
    }

    // Reminder toggle logic for Edit forms
    document.querySelectorAll('button[id^="set-reminder-"]').forEach(toggle => {
        const noteId = toggle.id.split('-')[2];
        const reminderDateInput = document.getElementById(`edit-reminder-date-${noteId}`);
        const setReminderHidden = document.getElementById(`set-reminder-hidden-${noteId}`);

        if (toggle && reminderDateInput && setReminderHidden) {
            toggle.addEventListener('click', () => {
                const currentState = toggle.getAttribute('data-state');
                const newState = currentState === 'on' ? 'off' : 'on';
                toggle.setAttribute('data-state', newState);
                toggle.textContent = newState === 'on' ? 'On' : 'Off';
                setReminderHidden.value = newState;
                reminderDateInput.disabled = newState !== 'on';
                if (newState !== 'on') {
                    reminderDateInput.value = '';
                }
            });

            // Prevent past dates
            const today = new Date().toISOString().split('T')[0];
            reminderDateInput.setAttribute('min', today);
        }
    });
});