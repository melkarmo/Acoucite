# Acoucite

This project is a data vizualisation webapp for noise measures in the Lyon area. 

*The noise measures were provided by Lyon-based non-profit organization [Acoucité](https://www.acoucite.org/).*

The application allows the visitor to choose a noise measuring station in the Lyon area using a Leaflet interactive map, a daytime range and a time period of measuring : a graphic of the noise levels is then generated and displayed in the application according to his input.

*Environment :*  
   (**Back**) Python 3, Socketserver, Httpserver, Matplotlib, SQLite  
   (**Front**) JavaScript, HTML/CSS, Leaflet
   
## Configuration

All the data is stored in `acoucite.sqlite`.   
   Start the back-end server by running `server.py` and go to http://localhost:8080/.

## Screenshots

![Capture1](https://raw.githubusercontent.com/melkarmo/Acoucite/master/screenshots/screenshot1.PNG)
![Capture2](https://raw.githubusercontent.com/melkarmo/Acoucite/master/screenshots/screenshot2.PNG)
