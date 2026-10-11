import cv2
import numpy as np
import boto3
import time
import datetime



AWS_ACCESS_KEY = 'YOUR_ACCESS_KEY'
AWS_SECRET_KEY = 'YOUR_SECRET_KEY'
AWS_REGION = 'ap-south-1' 
PHONE_NUMBER = '+919876543210'

CAMERA_LOC_NAME = "Main Road, Penuganchiprolu"
CAMERA_LAT = 16.9388
CAMERA_LNG = 80.1420

sns_client = boto3.client('sns', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=AWS_REGION)

last_alert_time = 0
COOLDOWN_SECONDS = 60
sns_client = boto3.client(
    'sns',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)


last_alert_time = 0
COOLDOWN_SECONDS = 60 


global_state = {
    "water_level": 0,
    "road_damage": 0,
    "status": "SAFE",
    "logs": [f"{datetime.datetime.now().strftime('%I:%M:%S %p')} - SYSTEM ONLINE: Monitoring active."], # <-- ఇక్కడ మార్చాం
    "location": CAMERA_LOC_NAME,
    "lat": CAMERA_LAT,
    "lng": CAMERA_LNG
}

def add_log(message):
    time_str = datetime.datetime.now().strftime("%I:%M:%S %p")
    global_state["logs"].insert(0, f"{time_str} - {message}")
    if len(global_state["logs"]) > 5:
        global_state["logs"].pop()

def trigger_aws_sms(alert_type, percentage):
    global last_alert_time
    current_time = time.time()
    
    if current_time - last_alert_time > COOLDOWN_SECONDS:
        if alert_type == "FLOOD":
            message = f"🚨 WATER DEPT ALERT: Flood detected in Ward 4. Water level: {percentage}%. Dispatch emergency clearing team."
        elif alert_type == "ROAD":
            message = f"⚠️ R&B DEPT ALERT: Major road damage/pothole detected in Ward 4. Damage area: {percentage}%. Please schedule repairs."
            
        try:
            sns_client.publish(PhoneNumber=PHONE_NUMBER, Message=message)
            print(f"\nSUCCESS: {alert_type} SMS Sent to Officer!")
            last_alert_time = current_time 
        except Exception as e:
            print(f"\nAWS ERROR: {e}")

def generate_frames():
    cap = cv2.VideoCapture(0) 
    
    if not cap.isOpened():
        print("ERROR: Camera failed to open!")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break
            
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        total_area = frame.shape[0] * frame.shape[1]

        
        lower_mud = np.array([10, 50, 50])
        upper_mud = np.array([30, 255, 255])
        mask_water = cv2.inRange(hsv, lower_mud, upper_mud)
        contours_water, _ = cv2.findContours(mask_water, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        water_area = 0
        for contour in contours_water:
            if cv2.contourArea(contour) > 1000:
                water_area += cv2.contourArea(contour)
                cv2.drawContours(frame, [contour], -1, (255, 0, 0), 2) 
                
        water_percentage = (water_area / total_area) * 100
        global_state["water_level"] = int(water_percentage)

        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 50]) 
        mask_road = cv2.inRange(hsv, lower_dark, upper_dark)
        contours_road, _ = cv2.findContours(mask_road, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        damage_area = 0
        for contour in contours_road:
            if cv2.contourArea(contour) > 1500: 
                damage_area += cv2.contourArea(contour)
                cv2.drawContours(frame, [contour], -1, (0, 165, 255), 2) 
                
        damage_percentage = (damage_area / total_area) * 100
        global_state["road_damage"] = int(damage_percentage)

        
        if water_percentage > 20: 
            status_text = f"FLOOD ALERT: {int(water_percentage)}%"
            color = (0, 0, 255) 
            if global_state["status"] != "FLOOD_ALERT":
                global_state["status"] = "FLOOD_ALERT"
                add_log(f"CRITICAL: Flood detected ({int(water_percentage)}%)")
                trigger_aws_sms("FLOOD", int(water_percentage)) 

        elif damage_percentage > 15: 
            status_text = f"ROAD BROKEN: {int(damage_percentage)}%"
            color = (0, 165, 255) 
            if global_state["status"] != "ROAD_ALERT":
                global_state["status"] = "ROAD_ALERT"
                add_log(f"WARNING: Broken road detected ({int(damage_percentage)}%)")
                trigger_aws_sms("ROAD", int(damage_percentage))

        else:
            status_text = "SYSTEM SAFE"
            color = (0, 255, 0) 
            if global_state["status"] != "SAFE":
                global_state["status"] = "SAFE"
                add_log("SAFE: Street conditions normal.")
            
        cv2.putText(frame, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')