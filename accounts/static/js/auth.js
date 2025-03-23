function get_otp(csrf) {
    let email = document.getElementById("email").value;

    if (!email) {
        alert("Enter a valid email address");
        return;
    }

    fetch(`/send-otp/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf
        },
        body: JSON.stringify({ email })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        
        if (data.status === "error") {
            alert(data.message);
            return;
        }

        alert("OTP has been sent successfully!");
    })
    .catch(error => {
        console.error("Error sending OTP:", error);
        alert("Failed to send OTP. Please try again.");
    });
}
