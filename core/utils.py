import logging
from datetime import datetime
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

def send_welcome_email(user, raw_password):
    """
    Send a welcome email to the user with their login credentials.
    Using a minimal, professional HTML template.
    """
    if not user.email:
        logger.warning(f"User {user.username} has no email address. Skipping welcome email.")
        return

    subject = 'Welcome to Sabarmati Gas Limited - Account Credentials'
    
    # Minimal Professional HTML Template with Inline CSS
    html_message = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <title>Welcome to SGL</title>

        </head>
        <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;">
            <!-- Wrapper Table for Email Clients -->
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4; margin: 0; padding: 0;">
                <tr>
                    <td style="padding: 20px 0;">
                        <!-- Main Container -->
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                            
                            <!-- Header Section -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #0056b3 0%, #003d82 100%); padding: 35px 30px; text-align: center;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;">
                                        Sabarmati Gas Limited
                                    </h1>
                                    <p style="margin: 8px 0 0 0; color: #e0f0ff; font-size: 14px; font-weight: 400;">
                                        Your trusted energy partner
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Content Section -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <h2 style="margin: 0 0 20px 0; color: #0056b3; font-size: 22px; font-weight: 600;">
                                        Welcome Aboard! 🎉
                                    </h2>
                                    
                                    <p style="margin: 0 0 15px 0; color: #333333; font-size: 16px; line-height: 1.6;">
                                        Dear <strong style="color: #0056b3;">{user.get_full_name() or user.username}</strong>,
                                    </p>
                                    
                                    <p style="margin: 0 0 25px 0; color: #555555; font-size: 15px; line-height: 1.6;">
                                        We're excited to have you join Sabarmati Gas Limited! Your account has been successfully created. Below are your login credentials:
                                    </p>
                                    
                                    <!-- Credentials Box -->
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: linear-gradient(135deg, #f8fbff 0%, #e8f4ff 100%); border-radius: 8px; border: 2px solid #0056b3; margin: 25px 0;">
                                        <tr>
                                            <td style="padding: 25px;">
                                                <!-- Email Row -->
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 15px;">
                                                    <tr>
                                                        <td style="width: 35%; padding-right: 10px; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #0056b3;">
                                                                📧 Email:
                                                            </p>
                                                        </td>
                                                        <td style="width: 65%; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; color: #333333; font-family: 'Courier New', Courier, monospace; background-color: #ffffff; padding: 8px 12px; border-radius: 4px; border: 1px solid #d0d0d0; word-break: break-all;">
                                                                {user.email}
                                                            </p>
                                                        </td>
                                                    </tr>
                                                </table>
                                                
                                                <!-- Phone Row -->
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 15px;">
                                                    <tr>
                                                        <td style="width: 35%; padding-right: 10px; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #0056b3;">
                                                                📱 Phone:
                                                            </p>
                                                        </td>
                                                        <td style="width: 65%; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; color: #333333; font-family: 'Courier New', Courier, monospace; background-color: #ffffff; padding: 8px 12px; border-radius: 4px; border: 1px solid #d0d0d0;">
                                                                {user.phone if hasattr(user, 'phone') and user.phone else 'N/A'}
                                                            </p>
                                                        </td>
                                                    </tr>
                                                </table>
                                                
                                                <!-- Password Row -->
                                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                                    <tr>
                                                        <td style="width: 35%; padding-right: 10px; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; font-weight: 700; color: #0056b3;">
                                                                🔒 Password:
                                                            </p>
                                                        </td>
                                                        <td style="width: 65%; vertical-align: top;">
                                                            <p style="margin: 0; font-size: 14px; color: #333333; font-family: 'Courier New', Courier, monospace; background-color: #ffffff; padding: 8px 12px; border-radius: 4px; border: 1px solid #d0d0d0; word-break: break-all;">
                                                                {raw_password}
                                                            </p>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- Security Notice -->
                                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin: 25px 0;">
                                        <tr>
                                            <td style="padding: 15px 20px;">
                                                <p style="margin: 0; color: #856404; font-size: 14px; line-height: 1.5;">
                                                    <strong>⚠️ Important Security Notice:</strong><br>
                                                    Please log in and change your password immediately for security purposes.
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="margin: 25px 0 0 0; color: #777777; font-size: 14px; line-height: 1.6;">
                                        If you have any questions or need assistance, please don't hesitate to contact our support team.
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Footer Section -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e0e0e0;">
                                    <p style="margin: 0 0 10px 0; color: #666666; font-size: 13px; text-align: center; line-height: 1.5;">
                                        <strong>Sabarmati Gas Limited</strong><br>
                                        Your trusted energy partner
                                    </p>
                                    
                                    <p style="margin: 10px 0 0 0; color: #999999; font-size: 12px; text-align: center; line-height: 1.4;">
                                        © {datetime.now().year} Sabarmati Gas Limited. All rights reserved.<br>
                                        This is an automated message. Please do not reply to this email.
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
    """
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {e}")


def send_otp_email(user, otp):
    """
    Send OTP for password reset.
    """
    if not user.email:
         return
         
    subject = 'Password Reset OTP - Sabarmati Gas Limited'
    
    html_message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>SGL Password Reset</title>
    </head>
    <body style="font-family: 'Segoe UI', sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; border: 1px solid #ddd;">
            <h2 style="color: #0056b3; margin-top: 0;">Password Reset Request</h2>
            <p>Dear {user.full_name},</p>
            <p>You have requested to reset your password. Please use the following OTP to proceed:</p>
            
            <div style="background: #f0f7ff; padding: 15px; text-align: center; border-radius: 4px; margin: 20px 0;">
                <span style="font-size: 32px; font-family: monospace; font-weight: bold; letter-spacing: 5px; color: #0056b3;">{otp}</span>
            </div>
            
            <p>This OTP is valid for 10 minutes.</p>
            <p style="color: #666; font-size: 13px;">If you did not request this, please ignore this email.</p>
        </div>
    </body>
    </html>
    """
    
    send_mail(subject, strip_tags(html_message), settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message, fail_silently=True)


def send_reset_success_email(user):
    """
    Send confirmation of password reset.
    """
    if not user.email:
         return

    subject = 'Password Reset Successful - Sabarmati Gas Limited'
    
    html_message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; border: 1px solid #ddd;">
            <h2 style="color: #28a745; margin-top: 0;">Success!</h2>
            <p>Dear {user.full_name},</p>
            <p>Your password and MPIN have been successfully reset.</p>
            <p>You can now login with your new credentials.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #888; font-size: 12px;">
                Sabarmati Gas Limited
            </div>
        </div>
    </body>
    </html>
    """
    
    send_mail(subject, strip_tags(html_message), settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message, fail_silently=True)
