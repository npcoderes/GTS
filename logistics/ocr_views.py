# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# import pytesseract
# from PIL import Image
# import base64
# import io
# import re
# import cv2
# import numpy as np
# import os
# import platform
# import logging

# # Configure Tesseract path for Windows
# if platform.system() == 'Windows':
#     # Common installation paths for Tesseract on Windows
#     possible_paths = [
#         r'C:\Program Files\Tesseract-OCR\tesseract.exe',
#         r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
#         os.path.expanduser('~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'),
#     ]
#     for path in possible_paths:
#         if os.path.exists(path):
#             pytesseract.pytesseract.tesseract_cmd = path
#             break


# class OCRExtractTextView(APIView):
#     """
#     OCR API endpoint to extract text and numbers from base64 encoded images
#     """
#     permission_classes = [IsAuthenticated]

#     def preprocess_image(self, image):
#         """
#         Fast preprocessing for LED/LCD meter displays
#         """
#         # Convert PIL image to numpy array
#         img_array = np.array(image)

#         # Convert to grayscale
#         if len(img_array.shape) == 3:
#             gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
#         else:
#             gray = img_array

#         # Constants for image scaling
#         MIN_DIMENSION = 400
#         MIN_SCALE = 2.5
        
#         # Upscale for small images
#         height, width = gray.shape
#         if height < MIN_DIMENSION or width < MIN_DIMENSION:
#             scale = max(MIN_DIMENSION / height, MIN_DIMENSION / width, MIN_SCALE)
#             new_width = int(width * scale)
#             new_height = int(height * scale)
#             gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

#         processed_images = []

#         # 1. Inverted (for LED displays with bright numbers on dark background)
#         inverted = cv2.bitwise_not(gray)
#         processed_images.append(inverted)

#         # 2. Original
#         processed_images.append(gray.copy())

#         # 3. Threshold inverted (works best for red LED on black)
#         try:
#             _, thresh_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
#             processed_images.append(thresh_inv)
#         except cv2.error:
#             pass

#         return processed_images

#     def _score_text_quality(self, text):
#         """Score text quality for OCR result selection"""
#         text_clean = text.replace('\n', ' ').strip()
#         if len(text_clean) < 1:
#             return 0
            
#         total_chars = len(text_clean)
#         digit_chars = sum(c.isdigit() for c in text_clean)
#         alpha_chars = sum(c.isalpha() for c in text_clean)
        
#         # Reject if too many weird characters
#         weird_chars = sum(1 for c in text_clean if not (c.isalnum() or c in ' .,@-+():;!?'))
#         if weird_chars > total_chars * 0.3:
#             return 0
            
#         digit_ratio = digit_chars / total_chars
#         alpha_ratio = alpha_chars / total_chars
        
#         if digit_ratio > 0.5:  # Numeric content
#             return digit_chars * 200 + len(text_clean) * 10
#         elif alpha_ratio > 0.5:  # Text content
#             words = text_clean.split()
#             valid_words = sum(1 for w in words if len(w) > 1 and sum(c.isalpha() for c in w) / len(w) >= 0.7)
#             return valid_words * 100 + len(text_clean) * 5
#         else:  # Mixed content
#             return len(text_clean) * 10 + (digit_chars + alpha_chars) * 5
    
#     def _select_best_result(self, results):
#         """Select best OCR result from multiple candidates"""
#         if not results:
#             return ""
            
#         scored = [(r, self._score_text_quality(r)) for r in results]
#         scored.sort(key=lambda x: x[1], reverse=True)
        
#         if scored and scored[0][1] > 0:
#             return scored[0][0]
            
#         # Fallback: prefer results with digits or letters
#         digits_results = [r for r in results if any(c.isdigit() for c in r)]
#         if digits_results:
#             return max(digits_results, key=lambda x: sum(c.isdigit() for c in x))
#         return max(results, key=lambda x: sum(c.isalpha() for c in x)) if results else ""

#     def extract_text_from_image(self, img, lang='eng'):
#         """
#         OCR with multiple configs for best results
#         """
#         results = []

#         # Try different PSM modes and configurations
#         configs = [
#             '',  # Default - works well for most cases
#             '--psm 6',  # Assume uniform block of text
#             '--psm 3',  # Fully automatic page segmentation
#             '--psm 11',  # Sparse text
#             '--psm 7 -c tessedit_char_whitelist=0123456789.',  # Single line digits only (for meters)
#             '--psm 8 -c tessedit_char_whitelist=0123456789.',  # Single word digits only
#         ]

#         for config in configs:
#             try:
#                 text = pytesseract.image_to_string(img, lang=lang, config=config)
#                 if text.strip() and text.strip() not in results:
#                     results.append(text.strip())
#             except Exception:
#                 pass

#         return results

#     def post(self, request):
#         """
#         Extract text from base64 image with advanced preprocessing

#         Expected payload:
#         {
#             "image": "base64_encoded_image_string",
#             "lang": "eng"  # Optional: language for OCR (default: eng)
#         }

#         Returns:
#         {
#             "success": true,
#             "extracted_text": "Full extracted text",
#             "all_results": ["result1", "result2"],
#             "numbers": ["123", "456"],
#             "text_only": "Text without numbers",
#             "confidence": 95.5
#         }
#         """
#         try:
#             # Get base64 image from request
#             image_data = request.data.get('image')
#             lang = request.data.get('lang', 'eng')

#             if not image_data:
#                 return Response({
#                     'success': False,
#                     'error': 'No image data provided'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Remove data URI prefix if present
#             if ',' in image_data:
#                 image_data = image_data.split(',')[1]

#             # Decode base64 image with proper resource management
#             try:
#                 image_bytes = base64.b64decode(image_data)
#                 with io.BytesIO(image_bytes) as img_buffer:
#                     image = Image.open(img_buffer).copy()
#             except Exception as e:
#                 return Response({
#                     'success': False,
#                     'error': f'Invalid image data: {str(e)}'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Convert image to RGB if necessary
#             if image.mode != 'RGB':
#                 image = image.convert('RGB')

#             # Preprocess image (returns multiple versions)
#             processed_images = self.preprocess_image(image)

#             # Collect all text results from different preprocessing methods
#             all_text_results = []
#             all_confidences = []

#             # Try OCR on each preprocessed image
#             for proc_img in processed_images:
#                 # Convert numpy array back to PIL Image
#                 pil_img = Image.fromarray(proc_img)

#                 # Extract text using multiple methods
#                 texts = self.extract_text_from_image(pil_img, lang)
#                 all_text_results.extend(texts)

#                 # Get confidence for this image
#                 try:
#                     data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)
#                     confidences = [int(conf) for conf in data['conf'] if conf != '-1']
#                     if confidences:
#                         avg_conf = sum(confidences) / len(confidences)
#                         all_confidences.append(avg_conf)
#                 except Exception:
#                     pass

#             # Also try the original image
#             original_texts = self.extract_text_from_image(image, lang)
#             all_text_results.extend(original_texts)

#             # Remove duplicates while preserving order
#             unique_results = []
#             seen = set()
#             for text in all_text_results:
#                 # Clean the text before deduplication
#                 cleaned = text.strip()
#                 cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace

#                 normalized = cleaned.lower()
#                 if normalized and normalized not in seen:
#                     seen.add(normalized)
#                     unique_results.append(cleaned)

#             # Find the best result based on quality metrics
#             best_result = self._select_best_result(unique_results)

#             # Calculate average confidence
#             avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else None

#             # Extract numbers from best result
#             numbers = re.findall(r'\d+\.?\d*', best_result)

#             # Clean up the extracted text
#             cleaned_text = best_result.strip()
#             # Remove excessive whitespace and newlines
#             cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
#             # DON'T remove @ symbols - they're valid in emails
#             cleaned_text = re.sub(r'\s*\|\s*', ' ', cleaned_text)  # Remove pipe symbols
#             # Fix spacing issues
#             cleaned_text = re.sub(r'\s([.,;:!?])', r'\1', cleaned_text)  # Remove space before punctuation
#             cleaned_text = cleaned_text.strip()

#             # Extract text without numbers
#             text_only = re.sub(r'\d+\.?\d*', '', cleaned_text).strip()
#             text_only = re.sub(r'\s+', ' ', text_only)

#             return Response({
#                 'success': True,
#                 'extracted_text': cleaned_text,
#                 'numbers': numbers,
#                 'text_only': text_only,
#                 'confidence': round(avg_confidence, 2) if avg_confidence else None
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             logging.error(f'OCR extraction failed: {str(e)}')
#             return Response({
#                 'success': False,
#                 'error': 'OCR extraction failed'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)