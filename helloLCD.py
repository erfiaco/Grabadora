import LCD_I2C_classe as LCD

lcd = LCD.LCD_I2C()

lcd.write("hello world")
        
GPIO.cleanup()
lcd.clear()

