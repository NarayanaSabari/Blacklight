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
        candidate_name: str,
        candidate_data: dict = None,
        hr_edited_fields: list = None
    ) -> bool:
        """
        Send approval email to candidate with full profile details.
        
        Args:
            tenant_id: Tenant ID
            to_email: Candidate email
            candidate_name: Candidate name for greeting
            candidate_data: Dictionary with full candidate profile data
            hr_edited_fields: List of field names that were edited by HR
        """
        smtp_config = EmailService._get_tenant_smtp_config(tenant_id)
        if not smtp_config:
            return False
        
        company_name = smtp_config.get('from_name', 'Our Company')
        candidate_data = candidate_data or {}
        hr_edited_fields = hr_edited_fields or []
        
        # Helper to format field with HR edit indicator
        def format_field(label: str, value, field_name: str) -> str:
            if not value:
                return ""
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">Updated by HR</span>' if field_name in hr_edited_fields else ""
            return f'<tr><td style="padding: 8px 12px; color: #6b7280; width: 160px; vertical-align: top;">{label}</td><td style="padding: 8px 12px;"><strong>{value}</strong>{edit_badge}</td></tr>'
        
        # Build profile sections
        # Personal Information
        personal_info = ""
        personal_info += format_field("Full Name", candidate_data.get('full_name'), 'full_name')
        personal_info += format_field("Email", candidate_data.get('email'), 'email')
        personal_info += format_field("Phone", candidate_data.get('phone'), 'phone')
        personal_info += format_field("Location", candidate_data.get('location'), 'location')
        if candidate_data.get('linkedin_url'):
            linkedin = f'<a href="{candidate_data.get("linkedin_url")}" style="color: #2563eb;">LinkedIn Profile</a>'
            personal_info += format_field("LinkedIn", linkedin, 'linkedin_url')
        if candidate_data.get('portfolio_url'):
            portfolio = f'<a href="{candidate_data.get("portfolio_url")}" style="color: #2563eb;">Portfolio</a>'
            personal_info += format_field("Portfolio", portfolio, 'portfolio_url')
        
        # Professional Information
        professional_info = ""
        professional_info += format_field("Current Title", candidate_data.get('current_title'), 'current_title')
        if candidate_data.get('total_experience_years'):
            exp_years = candidate_data.get('total_experience_years')
            exp_text = f"{exp_years} year{'s' if exp_years != 1 else ''}"
            professional_info += format_field("Experience", exp_text, 'total_experience_years')
        professional_info += format_field("Expected Salary", candidate_data.get('expected_salary'), 'expected_salary')
        
        # Summary
        summary_section = ""
        if candidate_data.get('professional_summary'):
            summary = candidate_data.get('professional_summary')
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'professional_summary' in hr_edited_fields else ""
            summary_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Professional Summary{edit_badge}</h3>
                <p style="background-color: #f9fafb; padding: 15px; border-radius: 8px; color: #374151; line-height: 1.6;">{summary}</p>
            </div>
            '''
        
        # Skills
        skills_section = ""
        skills = candidate_data.get('skills', [])
        if skills:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'skills' in hr_edited_fields else ""
            skills_html = ' '.join([f'<span style="background-color: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 12px; font-size: 13px; display: inline-block; margin: 3px;">{skill}</span>' for skill in skills[:15]])
            skills_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Skills{edit_badge}</h3>
                <div>{skills_html}</div>
            </div>
            '''
        
        # Preferred Roles
        roles_section = ""
        preferred_roles = candidate_data.get('preferred_roles', [])
        if preferred_roles:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'preferred_roles' in hr_edited_fields else ""
            roles_html = ' '.join([f'<span style="background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 12px; font-size: 13px; display: inline-block; margin: 3px;">{role}</span>' for role in preferred_roles])
            roles_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Preferred Roles{edit_badge}</h3>
                <div>{roles_html}</div>
            </div>
            '''
        
        # Education
        education_section = ""
        education = candidate_data.get('education', [])
        if education:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'education' in hr_edited_fields else ""
            edu_items = []
            for edu in education[:3]:  # Limit to 3
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                year = edu.get('graduation_year', '')
                edu_items.append(f'<li style="margin-bottom: 8px;"><strong>{degree}</strong> - {institution} {f"({year})" if year else ""}</li>')
            education_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Education{edit_badge}</h3>
                <ul style="margin: 0; padding-left: 20px; color: #374151;">{"".join(edu_items)}</ul>
            </div>
            '''
        
        # Work Experience
        experience_section = ""
        work_experience = candidate_data.get('work_experience', [])
        if work_experience:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'work_experience' in hr_edited_fields else ""
            exp_items = []
            for exp in work_experience[:3]:  # Limit to 3
                title = exp.get('title', '')
                company = exp.get('company', '')
                start = exp.get('start_date', '')
                end = exp.get('end_date', 'Present')
                is_current = exp.get('is_current', False)
                period = f"{start} - {'Present' if is_current else end}" if start else ""
                exp_items.append(f'<li style="margin-bottom: 10px;"><strong>{title}</strong> at {company}<br/><span style="color: #6b7280; font-size: 13px;">{period}</span></li>')
            experience_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Work Experience{edit_badge}</h3>
                <ul style="margin: 0; padding-left: 20px; color: #374151; list-style-type: none;">{"".join(exp_items)}</ul>
            </div>
            '''
        
        # Certifications
        certifications_section = ""
        certifications = candidate_data.get('certifications', [])
        if certifications:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'certifications' in hr_edited_fields else ""
            certs_html = ' '.join([f'<span style="background-color: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 12px; font-size: 13px; display: inline-block; margin: 3px;">{cert}</span>' for cert in certifications])
            certifications_section = f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #374151; margin-bottom: 10px; font-size: 16px;">Certifications{edit_badge}</h3>
                <div>{certs_html}</div>
            </div>
            '''
        
        # Languages
        languages_section = ""
        languages = candidate_data.get('languages', [])
        if languages:
            edit_badge = ' <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span>' if 'languages' in hr_edited_fields else ""
            langs_html = ', '.join(languages)
            languages_section = f'''
            <div style="margin-top: 15px;">
                <span style="color: #6b7280;">Languages:</span> <strong>{langs_html}</strong>{edit_badge}
            </div>
            '''
        
        # HR edits notice
        hr_notice = ""
        if hr_edited_fields:
            hr_notice = f'''
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 25px; border-radius: 0 8px 8px 0;">
                <p style="margin: 0; color: #92400e;">
                    <strong>📝 Note:</strong> Some fields in your profile were updated by our HR team during the review process. 
                    Fields marked with <span style="background-color: #fef3c7; color: #92400e; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Updated by HR</span> 
                    have been modified. If you have any questions about these changes, please contact us.
                </p>
            </div>
            '''
        
        subject = f"Welcome to {company_name}! Your Profile Has Been Approved 🎉"
        
        body_html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto; background-color: #f3f4f6; padding: 20px;">
            <div style="background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Congratulations!</h1>
                    <p style="color: #bbf7d0; margin: 10px 0 0 0; font-size: 16px;">Your profile has been approved</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    <p style="font-size: 18px; color: #374151;">Hi <strong>{candidate_name}</strong>,</p>
                    
                    <p style="color: #4b5563;">Great news! Your candidate profile with <strong>{company_name}</strong> has been reviewed and approved. 
                    You are now part of our talent pipeline!</p>
                    
                    {hr_notice}
                    
                    <!-- Profile Summary Card -->
                    <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-top: 25px;">
                        <h2 style="color: #1f2937; margin: 0 0 15px 0; font-size: 18px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px;">📋 Your Approved Profile</h2>
                        
                        <!-- Personal Information -->
                        <h3 style="color: #374151; margin: 15px 0 10px 0; font-size: 16px;">Contact Information</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            {personal_info}
                        </table>
                        
                        <!-- Professional Information -->
                        {f'<h3 style="color: #374151; margin: 20px 0 10px 0; font-size: 16px;">Professional Details</h3><table style="width: 100%; border-collapse: collapse;">{professional_info}</table>' if professional_info else ''}
                    </div>
                    
                    {summary_section}
                    {skills_section}
                    {roles_section}
                    {experience_section}
                    {education_section}
                    {certifications_section}
                    {languages_section}
                    
                    <!-- Next Steps -->
                    <div style="margin-top: 30px; background-color: #eff6ff; border-radius: 8px; padding: 20px;">
                        <h3 style="color: #1e40af; margin: 0 0 15px 0; font-size: 16px;">📌 What's Next?</h3>
                        <ul style="margin: 0; padding-left: 20px; color: #374151;">
                            <li style="margin-bottom: 8px;">Your profile is now active in our system</li>
                            <li style="margin-bottom: 8px;">Our recruiters will reach out when relevant opportunities arise</li>
                            <li style="margin-bottom: 8px;">You can contact us anytime to update your profile</li>
                        </ul>
                    </div>
                    
                    <p style="margin-top: 30px; color: #4b5563;">If you have any questions, feel free to reach out to us.</p>
                    
                    <p style="margin-top: 20px;">
                        Best regards,<br>
                        <strong>{company_name} HR Team</strong>
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                    <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                        This email was sent by {company_name} via Blacklight Recruiting Platform
                    </p>
                </div>
            </div>
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
                    <li>Set up your team by inviting Managers and Recruiters</li>
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
        - Set up your team by inviting Managers and Recruiters
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
