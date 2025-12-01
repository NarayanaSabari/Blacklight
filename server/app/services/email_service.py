"""
Email Service
Handles email sending with SMTP configuration per tenant
"""
import logging
import smtplib
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
from sqlalchemy import select

from app import db
from app.models.tenant import Tenant
from config.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2
    
    @staticmethod
    def _get_tenant_smtp_config(tenant_id: int) -> Optional[Dict]:
        """
        Get SMTP configuration for a tenant.
        First checks tenant.settings.smtp_config, falls back to global .env config.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            SMTP config dict or None if not configured
        """
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return None
        
        # Try tenant-specific SMTP config first
        if tenant.settings and 'smtp_config' in tenant.settings:
            smtp_config = tenant.settings['smtp_config']
            
            # Validate required fields
            required_fields = ['host', 'port', 'username', 'password', 'from_email']
            if all(field in smtp_config for field in required_fields):
                logger.info(f"Using tenant-specific SMTP config for tenant {tenant_id}")
                return smtp_config
            else:
                logger.warning(f"Tenant {tenant_id} has incomplete SMTP config, falling back to global")
        
        # Fall back to global SMTP config from .env
        if settings.smtp_enabled:
            logger.info(f"Using global SMTP config for tenant {tenant_id}")
            return {
                'host': settings.smtp_host,
                'port': settings.smtp_port,
                'username': settings.smtp_username,
                'password': settings.smtp_password,
                'from_email': settings.smtp_from_email,
                'from_name': settings.smtp_from_name,
                'use_tls': settings.smtp_use_tls
            }
        
        logger.warning(f"No SMTP config found for tenant {tenant_id}")
        return None
    
    @staticmethod
    def _send_email(
        to: str,
        subject: str,
        body_html: str,
        smtp_config: Dict,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send email via SMTP with retry logic.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body_html: HTML body content
            smtp_config: SMTP configuration dict
            body_text: Optional plain text body (fallback)
            
        Returns:
            True if sent successfully, False otherwise
        """
        for attempt in range(1, EmailService.MAX_RETRIES + 1):
            try:
                # Create message
                message = MIMEMultipart('alternative')
                message['From'] = smtp_config.get('from_email')
                message['To'] = to
                message['Subject'] = subject
                
                # Add plain text part (if provided)
                if body_text:
                    part1 = MIMEText(body_text, 'plain')
                    message.attach(part1)
                
                # Add HTML part
                part2 = MIMEText(body_html, 'html')
                message.attach(part2)
                
                # Connect to SMTP server
                use_tls = smtp_config.get('use_tls', True)
                host = smtp_config['host']
                port = smtp_config['port']
                
                if use_tls:
                    server = smtplib.SMTP(host, port)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(host, port)
                
                # Login
                server.login(smtp_config['username'], smtp_config['password'])
                
                # Send email
                server.send_message(message)
                server.quit()
                
                logger.info(f"Email sent successfully to {to} (attempt {attempt})")
                return True
                
            except Exception as e:
                logger.error(f"Email send error (attempt {attempt}/{EmailService.MAX_RETRIES}): {e}")
                
                if attempt < EmailService.MAX_RETRIES:
                    time.sleep(EmailService.RETRY_DELAY_SECONDS * attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to send email to {to} after {EmailService.MAX_RETRIES} attempts")
                    return False
        
        return False
    
    @staticmethod
    def send_invitation_email(
        tenant_id: int,
        to_email: str,
        candidate_name: Optional[str],
        onboarding_url: str,
        expiry_date: str
    ) -> bool:
        """
        Send invitation email to candidate.
        
        Args:
            tenant_id: Tenant ID
            to_email: Candidate email
            candidate_name: Candidate name (if available)
            onboarding_url: Full URL to onboarding portal with token
            expiry_date: Formatted expiry date string
            
        Returns:
            True if sent successfully
        """
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            logger.error(f"Cannot send invitation email - no SMTP config for tenant {tenant_id}")
            return False
        
        company_name = smtp_config.get('from_name', 'Our Company')
        greeting = f"Hi {candidate_name}" if candidate_name else "Hi"
        
        subject = f"You're invited to join {company_name}"
        
        # HTML email body
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2563eb;">{greeting},</h2>
            
            <p>We're excited to invite you to join <strong>{company_name}</strong>!</p>
            
            <p>To get started, please complete your candidate profile using the link below:</p>
            
            <p style="margin: 30px 0;">
                <a href="{onboarding_url}" 
                   style="background-color: #2563eb; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Complete Your Profile
                </a>
            </p>
            
            <p><strong>Important:</strong> This link will expire on <strong>{expiry_date}</strong>. 
               Please complete your profile before then.</p>
            
            <p><strong>What you'll need to do:</strong></p>
            <ul>
                <li>Fill in your personal and professional details</li>
                <li>Upload your resume</li>
                <li>Upload required documents (ID proof, work authorization, etc.)</li>
            </ul>
            
            <p>If you have any questions, feel free to reach out to us.</p>
            
            <p>Looking forward to learning more about you!</p>
            
            <p>Best regards,<br>
            <strong>{company_name} HR Team</strong></p>
            
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
            <p style="font-size: 12px; color: #666;">
                This is an automated email. Please do not reply directly to this message.
            </p>
        </body>
        </html>
        """
        
        # Plain text fallback
        body_text = f"""
        {greeting},
        
        We're excited to invite you to join {company_name}!
        
        To get started, please complete your candidate profile using this link:
        {onboarding_url}
        
        This link will expire on {expiry_date}. Please complete your profile before then.
        
        What you'll need to do:
        - Fill in your personal and professional details
        - Upload your resume
        - Upload required documents (ID proof, work authorization, etc.)
        
        If you have any questions, feel free to reach out to us.
        
        Looking forward to learning more about you!
        
        Best regards,
        {company_name} HR Team
        
        ---
        This is an automated email. Please do not reply directly to this message.
        """
        
        return EmailService._send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            smtp_config=smtp_config
        )
    
    @staticmethod
    def send_submission_confirmation(
        tenant_id: int,
        to_email: str,
        candidate_name: str
    ) -> bool:
        """
        Send confirmation email after candidate submits.
        
        Args:
            tenant_id: Tenant ID
            to_email: Candidate email
            candidate_name: Candidate name
            
        Returns:
            True if sent successfully
        """
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            return False
        
        company_name = smtp_config.get('from_name', 'Our Company')
        
        subject = "We've received your submission"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2563eb;">Hi {candidate_name},</h2>
            
            <p>Thank you for completing your profile with <strong>{company_name}</strong>!</p>
            
            <p>We've received your information and our HR team is currently reviewing your submission. 
               We'll get back to you within 2-3 business days.</p>
            
            <p><strong>What happens next:</strong></p>
            <ul>
                <li>Our team will review your details and documents</li>
                <li>If approved, you'll receive a welcome email with next steps</li>
                <li>If we need any additional information, we'll reach out</li>
            </ul>
            
            <p>Thank you for your patience!</p>
            
            <p>Best regards,<br>
            <strong>{company_name} HR Team</strong></p>
        </body>
        </html>
        """
        
        return EmailService._send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            smtp_config=smtp_config
        )
    
    @staticmethod
    def send_hr_notification(
        tenant_id: int,
        hr_emails: List[str],
        candidate_name: str,
        candidate_email: str,
        invitation_id: int,
        review_url: str
    ) -> bool:
        """
        Send notification to HR team about new submission.
        
        Args:
            tenant_id: Tenant ID
            hr_emails: List of HR user emails
            candidate_name: Candidate name
            candidate_email: Candidate email
            invitation_id: Invitation ID
            review_url: URL to review submission
            
        Returns:
            True if sent successfully to at least one recipient
        """
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            return False
        
        subject = f"[ACTION REQUIRED] New candidate submission - {candidate_name}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #dc2626;">Action Required: New Candidate Submission</h2>
            
            <p>A new candidate has completed their self-onboarding submission and is awaiting your review.</p>
            
            <table style="width: 100%; max-width: 500px; border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9fafb;">
                        <strong>Candidate:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {candidate_name}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9fafb;">
                        <strong>Email:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        {candidate_email}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f9fafb;">
                        <strong>Invitation ID:</strong>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        #{invitation_id}
                    </td>
                </tr>
            </table>
            
            <p style="margin: 30px 0;">
                <a href="{review_url}" 
                   style="background-color: #2563eb; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Review Submission Now
                </a>
            </p>
            
            <p>Please review and approve/reject the submission at your earliest convenience.</p>
            
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
            <p style="font-size: 12px; color: #666;">
                Blacklight Recruiting Platform - Automated Notification
            </p>
        </body>
        </html>
        """
        
        success_count = 0
        for hr_email in hr_emails:
            if EmailService._send_email(
                to=hr_email,
                subject=subject,
                body_html=body_html,
                smtp_config=smtp_config
            ):
                success_count += 1
        
        logger.info(f"Sent HR notification to {success_count}/{len(hr_emails)} recipients")
        return success_count > 0
    
    @staticmethod
    def send_approval_email(
        tenant_id: int,
        to_email: str,
        candidate_name: str
    ) -> bool:
        """Send approval email to candidate"""
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            return False
        
        company_name = smtp_config.get('from_name', 'Our Company')
        
        subject = f"Welcome to {company_name}! 🎉"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #16a34a;">Hi {candidate_name},</h2>
            
            <p>Great news! Your candidate profile has been approved.</p>
            
            <p>Welcome to <strong>{company_name}</strong>! We're excited to have you in our talent pipeline.</p>
            
            <p><strong>What's next:</strong></p>
            <ul>
                <li>Your profile is now active in our system</li>
                <li>Our recruiters will reach out for relevant opportunities</li>
                <li>You can update your profile anytime by contacting us</li>
            </ul>
            
            <p>If you have any questions, feel free to reach out.</p>
            
            <p>Best regards,<br>
            <strong>{company_name} HR Team</strong></p>
        </body>
        </html>
        """
        
        return EmailService._send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            smtp_config=smtp_config
        )
    
    @staticmethod
    def send_tenant_welcome_email(
        to_email: str,
        admin_name: str,
        tenant_name: str,
        temporary_password: str,
        login_url: str
    ) -> bool:
        """
        Send welcome email to new tenant admin with temporary credentials.
        Uses global SMTP config since tenant doesn't have SMTP configured yet.
        
        Args:
            to_email: Tenant admin email
            admin_name: Admin user's name
            tenant_name: Tenant company name
            temporary_password: Temporary password for first login
            login_url: URL to the portal login page
            
        Returns:
            True if sent successfully
        """
        # Use global SMTP config since this is for new tenant creation
        if not settings.smtp_enabled:
            logger.error("Cannot send tenant welcome email - SMTP not configured")
            return False
        
        smtp_config = {
            'host': settings.smtp_host,
            'port': settings.smtp_port,
            'username': settings.smtp_username,
            'password': settings.smtp_password,
            'from_email': settings.smtp_from_email,
            'from_name': settings.smtp_from_name or 'Blacklight Platform',
            'use_tls': settings.smtp_use_tls
        }
        
        subject = f"Welcome to Blacklight - Your {tenant_name} Account is Ready! 🎉"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Welcome to Blacklight</h1>
                <p style="color: #e0e7ff; margin: 10px 0 0 0;">Your HR Recruiting Platform</p>
            </div>
            
            <div style="padding: 30px; background-color: #f9fafb;">
                <h2 style="color: #1e40af;">Hi {admin_name},</h2>
                
                <p>Congratulations! Your organization <strong>{tenant_name}</strong> has been successfully set up on the Blacklight platform.</p>
                
                <p>You have been assigned as the <strong>Tenant Administrator</strong> for your organization. Here are your login credentials:</p>
                
                <div style="background-color: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;"><strong>Email:</strong></td>
                            <td style="padding: 8px 0;">{to_email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;"><strong>Temporary Password:</strong></td>
                            <td style="padding: 8px 0; font-family: monospace; background-color: #fef3c7; padding: 4px 8px; border-radius: 4px;">{temporary_password}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #dc2626;"><strong>⚠️ Important Security Notice:</strong></p>
                    <p style="margin: 10px 0 0 0;">Please change your password immediately after your first login for security purposes.</p>
                </div>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{login_url}" 
                       style="background-color: #1e40af; color: white; padding: 14px 32px; 
                              text-decoration: none; border-radius: 8px; display: inline-block;
                              font-weight: bold;">
                        Login to Your Dashboard
                    </a>
                </p>
                
                <h3 style="color: #1e40af;">Getting Started:</h3>
                <ul style="padding-left: 20px;">
                    <li>Login and change your password</li>
                    <li>Set up your team by inviting Hiring Managers and Recruiters</li>
                    <li>Start adding candidates or send onboarding invitations</li>
                    <li>Configure your organization's settings</li>
                </ul>
                
                <p>If you have any questions or need assistance, our support team is here to help.</p>
                
                <p>Welcome aboard!</p>
                
                <p>Best regards,<br>
                <strong>The Blacklight Team</strong></p>
            </div>
            
            <div style="background-color: #1f2937; padding: 20px; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This is an automated email from Blacklight Platform.<br>
                    Please do not reply directly to this message.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_text = f"""
        Welcome to Blacklight!
        
        Hi {admin_name},
        
        Congratulations! Your organization {tenant_name} has been successfully set up on the Blacklight platform.
        
        You have been assigned as the Tenant Administrator. Here are your login credentials:
        
        Email: {to_email}
        Temporary Password: {temporary_password}
        
        IMPORTANT: Please change your password immediately after your first login.
        
        Login URL: {login_url}
        
        Getting Started:
        - Login and change your password
        - Set up your team by inviting Hiring Managers and Recruiters
        - Start adding candidates or send onboarding invitations
        - Configure your organization's settings
        
        Welcome aboard!
        
        Best regards,
        The Blacklight Team
        """
        
        return EmailService._send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            smtp_config=smtp_config
        )
    
    @staticmethod
    def send_rejection_email(
        tenant_id: int,
        to_email: str,
        candidate_name: str,
        reason: Optional[str] = None
    ) -> bool:
        """Send rejection email to candidate"""
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            return False
        
        company_name = smtp_config.get('from_name', 'Our Company')
        
        subject = "Update on your submission"
        
        reason_html = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #2563eb;">Hi {candidate_name},</h2>
            
            <p>Thank you for taking the time to submit your profile to <strong>{company_name}</strong>.</p>
            
            <p>After reviewing your submission, we've decided not to proceed at this time.</p>
            
            {reason_html}
            
            <p>We encourage you to apply again in the future as new opportunities arise.</p>
            
            <p>Thank you for your interest in {company_name}.</p>
            
            <p>Best regards,<br>
            <strong>{company_name} HR Team</strong></p>
        </body>
        </html>
        """
        
        return EmailService._send_email(
            to=to_email,
            subject=subject,
            body_html=body_html,
            smtp_config=smtp_config
        )
