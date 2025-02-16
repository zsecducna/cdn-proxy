# AUTHOR(s): Dave Yesland @daveysec and Ryan Gerstenkorn @ryan_jarv, Rhino Security Labs @rhinosecurity
# Burp Suite extension which uses proxies requests through a CloudFront distribution set up with the cdn-proxy tool.
# More Info: https://github.com/RhinoSecurityLabs/cdn-proxy

from javax.swing import (
    JPanel,
    JTextField,
    JButton,
    JLabel,
    BoxLayout,
    JPasswordField,
    JCheckBox,
    JRadioButton,
    ButtonGroup,
)
from burp import IBurpExtender, IExtensionStateListener, ITab, IHttpListener

EXT_NAME = "CDN Proxy"
ENABLED = '<html><h2><font color="green">Enabled</font></h2></html>'
DISABLED = '<html><h2><font color="red">Disabled</font></h2></html>'
STAGE_NAME = "burpendpoint"
API_NAME = "BurpAPI"

class BurpExtender(IBurpExtender, IExtensionStateListener, ITab, IHttpListener):
    def __init__(self):
        self.isEnabled = False
        self.callbacks = None
        self.helpers = None

    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        self.helpers = callbacks.helpers

        callbacks.registerHttpListener(self)
        callbacks.registerExtensionStateListener(self)
        callbacks.setExtensionName(EXT_NAME)
        callbacks.addSuiteTab(self)

    # Traffic redirecting
    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        # only process requests
        if (
            not messageIsRequest or not self.isEnabled
        ):  # or not toolFlag == self.helpers.TOOL_PROXY:
            return

        # get the HTTP service for the request
        httpService = messageInfo.getHttpService()

        # Modify the request host, host header, and path to point to the new API endpoint
        # Should always use HTTPS because API Gateway only uses HTTPS
        proxy_host = self.proxy_host.text.split(":")[0]

        requestInfo = self.helpers.analyzeRequest(messageInfo)
        headers = requestInfo.getHeaders()

        messageInfo.setHttpService(
            self.helpers.buildHttpService(
                proxy_host, httpService.getPort(), httpService.getProtocol() == "https"
            )
        )

        # Replace the Host header with the Gateway host
        for i, header in enumerate(headers):
            if header.startswith("Host: "):
                # host_header_index = new_headers.index(header)
                # new_headers[host_header_index] = 'Host: ' + proxy_host
                print("Fund host header: " + header)
                headers[i] = "Host: " + proxy_host

        headers.add("Cdn-Proxy-Origin: {}".format(requestInfo.getUrl().getHost()))
        headers.add("Cdn-Proxy-Host: {}".format(requestInfo.getUrl().getHost()))
        print("headers: " + headers)

        # Update the headers insert the existing body
        body = messageInfo.request[requestInfo.getBodyOffset() :]
        messageInfo.request = self.helpers.buildHttpMessage(headers, body)

    # Tab name
    def getTabCaption(self):
        return EXT_NAME

    # Handle extension unloading
    def extensionUnloaded(self):
        if self.cloudfront:
            self.disable_proxy()

    def enable_proxy(self, event):
        self.isEnabled = True
        self.status_indicator.text = ENABLED
        self.enable_button.setEnabled(False)
        self.proxy_host.setEnabled(False)
        self.disable_button.setEnabled(True)

    def disable_proxy(self, event):
        self.isEnabled = False
        self.status_indicator.text = DISABLED
        self.enable_button.setEnabled(True)
        self.proxy_host.setEnabled(True)
        self.disable_button.setEnabled(False)

    # Layout the UI
    def getUiComponent(self):
        self.panel = JPanel()

        self.main = JPanel()
        self.main.setLayout(BoxLayout(self.main, BoxLayout.Y_AXIS))

        self.proxy_host_panel = JPanel()
        self.main.add(self.proxy_host_panel)
        self.proxy_host_panel.setLayout(
            BoxLayout(self.proxy_host_panel, BoxLayout.X_AXIS)
        )
        self.proxy_host_panel.add(JLabel("Proxy CDN Domain: "))
        self.proxy_host = JTextField("<dist id>.cloudfront.com", 25)
        self.proxy_host_panel.add(self.proxy_host)

        self.buttons_panel = JPanel()
        self.main.add(self.buttons_panel)
        self.buttons_panel.setLayout(BoxLayout(self.buttons_panel, BoxLayout.X_AXIS))
        self.enable_button = JButton("Enable", actionPerformed=self.enable_proxy)
        self.buttons_panel.add(self.enable_button)
        self.disable_button = JButton("Disable", actionPerformed=self.disable_proxy)
        self.buttons_panel.add(self.disable_button)
        self.disable_button.setEnabled(False)

        self.status = JPanel()
        self.main.add(self.status)
        self.status.setLayout(BoxLayout(self.status, BoxLayout.X_AXIS))
        self.status_indicator = JLabel(DISABLED, JLabel.CENTER)
        self.status.add(self.status_indicator)

        self.panel.add(self.main)

        return self.panel
