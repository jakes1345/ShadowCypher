# ... (Code modifications based on analysis and research) ...

    def generate_phishing_email(target_email, payload):
        """Generates a phishing email with modern techniques."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg['From'] = "ShadowCypher <shadowcypher@example.com>"  # Spoofed sender address
        msg['To'] = target_email
        msg['Subject'] = "Urgent Security Update Required"  # Attention-grabbing subject

        body = f"""
        **Important Notice:** Your account security has been compromised. 
        Please click the link below to verify your information and prevent further access:

        [Malicious Link]

        This is a critical action required to protect your account. 
        Failure to respond may result in permanent suspension.
        """
        msg.attach(MIMEText(body, 'html'))  # HTML formatting for better presentation

        return msg.as_string()


