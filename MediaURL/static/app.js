
let currentTicket = null;
let polling = null;

// ------------------
// STATUS UI
// ------------------
function updateStatus(msg) {
    document.getElementById("statusBox").innerText = msg;
}

// ------------------
// BUTTON CONTROL
// ------------------
function setButtons(processing, allowClose, allowStart) {

    document.getElementById("processBtn").disabled = !allowStart || processing;

    document.getElementById("closeBtn").disabled = !allowClose;
}

// ------------------
// START PROCESS
// ------------------
function processTicket() {

    currentTicket = parseInt(document.getElementById("ticketInput").value);

    if (!currentTicket) {
        updateStatus("Invalid Ticket ❌");
        return;
    }

    // LOCK START BUTTON IMMEDIATELY
    setButtons(true, false, false);

    updateStatus("Queued...");

    fetch("/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "ticket_id=" + currentTicket
    });

    startPolling();
}

// ------------------
// POLLING STATUS
// ------------------
function startPolling() {

    if (polling) clearInterval(polling);

    polling = setInterval(() => {

        fetch(`/status/${currentTicket}`)
        .then(r => r.json())
        .then(data => {

            const status = data.status;

            if (status === "processing") {
                updateStatus("Processing...");
                setButtons(true, false, false);
            }

            else if (status === "uploading") {
                updateStatus("Uploading...");
                setButtons(true, false, false);
            }

            else if (status === "reply_sent") {
                updateStatus("Reply Sent ✔");
            }

            else if (status === "agent_assigned") {
                updateStatus("Agent Assigned ✔");
            }

            else if (status === "ready_to_close") {
                updateStatus("Ready to Close ✔");

                // enable only close
                setButtons(false, true, false);

                clearInterval(polling);
            }

            else if (status === "closed") {
                updateStatus("Ticket Closed ✔");

                setButtons(false, false, true); // nothing allowed
            }

        });

    }, 2000);
}

// ------------------
// CLOSE
// ------------------
function closeTicket() {

    updateStatus("Closing ticket...");

    fetch("/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_id: currentTicket })
    })
    .then(r => r.json())
    .then(data => {

        updateStatus("Ticket Closed ✔");

        setButtons(false, false, true);
    });
}