# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from paddleocr import PaddleOCR
# from PIL import Image
# import base64
# import io
# import re
# import cv2
# import numpy as np
# import threading
# import logging

# # Thread-safe OCR reader initialization
# ocr_reader = None
# ocr_lock = threading.Lock()

# def get_paddle_reader():
#     global ocr_reader
#     if ocr_reader is None:
#         with ocr_lock:
#             if ocr_reader is None:
#                 ocr_reader = PaddleOCR(use_angle_cls=True, lang='en')
#     return ocr_reader


# class PaddleOCRExtractTextView(APIView):
#     """
#     OCR API using PaddleOCR - excellent for LED/LCD displays and meter readings
#     """
#     permission_classes = [IsAuthenticated]

#     def preprocess_for_ocr(self, image):
#         """
#         Preprocessing for general OCR (documents, business cards, etc.)
#         """
#         img_array = np.array(image)

#         # Convert RGB to BGR for PaddleOCR (it expects BGR format)
#         if len(img_array.shape) == 3:
#             bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
#         else:
#             # If grayscale, convert to BGR
#             bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

#         # Upscale small images for better accuracy
#         height, width = bgr.shape[:2]
#         if height < 600 or width < 600:
#             scale = max(600 / height, 600 / width)
#             new_width = int(width * scale)
#             new_height = int(height * scale)
#             bgr = cv2.resize(bgr, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

#         return bgr

#     def post(self, request):
#         """
#         Extract text/numbers from base64 image using PaddleOCR

#         Expected payload:
#         {
#             "image": "base64_encoded_image_string"
#         }

#         Returns:
#         {
#             "success": true,
#             "extracted_text": "236.5",
#             "all_detections": [
#                 {"text": "236.5", "confidence": 0.95},
#                 {"text": "2409", "confidence": 0.92}
#             ],
#             "numbers": ["236.5", "2409"],
#             "confidence": 93.5
#         }
#         """
#         try:
#             # Get base64 image
#             image_data = request.data.get('image')

#             if not image_data:
#                 return Response({
#                     'success': False,
#                     'error': 'No image data provided'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Remove data URI prefix
#             if ',' in image_data:
#                 image_data = image_data.split(',')[1]

#             # Decode image with proper resource management
#             try:
#                 image_bytes = base64.b64decode(image_data)
#                 with io.BytesIO(image_bytes) as img_buffer:
#                     image = Image.open(img_buffer).copy()
#             except Exception as e:
#                 return Response({
#                     'success': False,
#                     'error': f'Invalid image data: {str(e)}'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Convert to RGB
#             if image.mode != 'RGB':
#                 image = image.convert('RGB')

#             # Preprocess image
#             processed_image = self.preprocess_for_ocr(image)

#             # Get PaddleOCR reader
#             paddle_ocr = get_paddle_reader()

#             # Perform OCR
#             # PaddleOCR returns: [[[bbox], (text, confidence)], ...]
#             results = paddle_ocr.ocr(processed_image)

#             # Process results
#             all_detections = []
#             all_numbers = []
#             confidences = []

#             # PaddleOCR 3.x returns results in format: [[line1_results], [line2_results], ...]
#             # Each line is: [bbox, (text, confidence)]
#             if results and results[0]:
#                 for line in results[0]:
#                     if line and len(line) >= 2:
#                         # line format: [bbox_points, [text, confidence]]
#                         text = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
#                         confidence = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 0.0
#                         text = text.strip()

#                         # Extract numbers from the text
#                         nums = re.findall(r'\d*\.?\d+', text)

#                         # Keep all detections (both text and numbers)
#                         if text:
#                             all_detections.append({
#                                 'text': text,
#                                 'confidence': round(confidence * 100, 2)
#                             })
#                             if nums:
#                                 all_numbers.extend(nums)
#                             confidences.append(confidence * 100)


#             # Combine all detected text into one result
#             if all_detections:
#                 # Sort detections by position (top to bottom, left to right based on bbox)
#                 # For now, just join all text with spaces
#                 all_text = ' '.join([d['text'] for d in all_detections])

#                 # Find the longest single detection as the best result
#                 best = max(all_detections, key=lambda x: len(x['text']))
#                 extracted_text = all_text if len(all_text) > len(best['text']) else best['text']
#                 avg_confidence = sum(confidences) / len(confidences) if confidences else 0
#             else:
#                 extracted_text = ""
#                 all_text = ""
#                 avg_confidence = 0

#             return Response({
#                 'success': True,
#                 'extracted_text': extracted_text,
#                 'all_text': all_text,  # Combined text from all detections
#                 'all_detections': all_detections[:10],  # Top 10
#                 'numbers': all_numbers,
#                 'confidence': round(avg_confidence, 2)
#             }, status=status.HTTP_200_OK)

#         except Exception as e:
#             logging.error(f'OCR extraction failed: {str(e)}')
#             return Response({
#                 'success': False,
#                 'error': 'OCR extraction failed'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
