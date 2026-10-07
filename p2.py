import cv2
import numpy as np

def red_objects(frame):
    # Convert to HSV colour kaanke lighting change thava thi HSV ma aetlu farak naa pade
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Define HSV range for red colour (adjusted for lighting conditions)
    red1 = np.array([0, 70, 50])
    red2 = np.array([10, 255, 255])

    # Threshold the HSV image to get only red colours
    range = cv2.inRange(hsv, red1, red2)

    # Reduce noise using Gaussian Blur
    blur = cv2.GaussianBlur(range,(11,11),sigmaX=10,sigmaY=10)
    #sigma x ane aigma y aaju baaju nu circle na pixels ne use karine mean laine
    #wadhaare blur thay aena maate che
    cv2.imshow('Processed Mask (Debug)', blur)

    # Detect circles using Hough Circle Transform
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1,#to control resolution in the accumulator
        minDist=30,
        param1=50,#for edges
        param2=50,#select circles
        minRadius=10,
        maxRadius=100
    )
    contours,hierarchy = cv2.findContours(blur,cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    # loop through contours
    cv2.drawContours(frame, contours, -1, (0, 255, 0), 3)
    cv2.imshow('Contours', frame)

    gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)

# threshold
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # get centroid
    M = cv2.moments(thresh)
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])       
    print('cx:', cx, 'cy:', cy)

    # draw centroid
    result = blur.copy()
    x = int(cx)
    y = int(cy)
    r = 1
    cv2.circle(result, (x, y), r, (0, 0, 255), 2)

    # save results
    cv2.imwrite('holes_centroid.png', result)

    # show results
    cv2.imshow('thresh', thresh)
    cv2.imshow('result', result)

    if circles is not None:
        circles = np.uint16(np.around(circles)) 
        #unsigned in etle che kaanke drawing circles waara function ma non negative values joie che
        for (x, y, r) in circles[0, :]:
            # Draw the outer circle
            cv2.circle(frame, (x, y), r, (0, 255, 0), 10)
            # Draw the center of the circle
            cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)
    return frame


cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    output_frame = red_objects(frame)

    cv2.imshow('Red Object Detection (q to exit)', output_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()