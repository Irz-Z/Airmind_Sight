const widgetKey = widgetKeyMap[province];
if (widgetKey) {
const widgetContainer = document.getElementById('widget-container');
const widgetScript = document.createElement('script');
widgetScript.type = 'text/javascript';
widgetScript.src = `https://widget.iqair.com/script/widget_v3.0.js`;
widgetContainer.innerHTML = `<div name="airvisual_widget" key="${widgetKey}"></div>`;
widgetContainer.appendChild(widgetScript);
}