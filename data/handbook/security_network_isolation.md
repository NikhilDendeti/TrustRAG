# Isolating your work laptop from other devices in your home network

## Why

There are various reasons why you might want to isolate your work laptop from other devices in your home network:

- **Security concerns**. The security of individual devices on your home network might vary. Some are notoriously insecure (like some "smart" home devices) or some might simply lack the latest security patches. Isolating devices with poor security from your work laptop (and other sensitive private devices) can increase the security of your work laptop.
- **Privacy concerns**. GitLab is an all-remote company, with many of its employees working from home. As a side-effect, our work laptops typically end up being connected to the same network as our personal devices, which allows for network access between these two groups of devices and may raise privacy concerns.

## How

Many home routers allow connected devices to be isolated, which prevents any direct network communication between selected devices. This section walks you through setting up an isolated WiFi specifically for your work laptop. The goals specifically are:

- Prevent direct connections to and from your work laptop towards other devices in your home network.
- Prevent your work laptop from accessing your router's management interface.
- Have internet access with your work laptop (of course :smile: )

Note that devices connect using different bands (2.4GHz and 5GHz) are typically not isolated from each other. Likewise, devices connected to your router by cable are not separated from devices that are also connected through WiFi.

### Simple Isolation with Guest Network

Many modern WiFi routers have the capability to generate bridged guest networks that separate devices on the network from each other while keeping things easy to understand. Rather than using your router's built in guest network support for guests, you can instead use it for your work devices. This effectively works the same way as having untrusted guests connecting to your network and should isolate your work device from other devices connected to your home network.

While most routers implement guest networks as described, be aware that your router might implement guest networks differently. Check your router's manual for details.

Note that you will likely not be able to connect to shared resources in your home network such as file servers or shared printers.

### Use AI for Detailed Instructions For Your Router

These instructions currently pertain to using Anthropic Claude.

1. From the main Okta page, select the Claude tile.
2. On the left side, click on Projects and select "Home network security strengthening".
3. Click on the pencil in the Instructions section and read them. You will need to copy and paste the prompt in, then insert your router's Make and Model, a working and recent URL for the router's user manual, and specify whether you use a Mac or Linux.
4. After you hit return, Claude may ask you a few questions that are numbered. Type in the number and answer the question but hitting shift+return instead of just return after each question.
5. After the final question simply hit return.
6. You should receive a PDF that has detailed instruction for isolating your work laptop on your home network, which should include a checklist.

**Note**. Feel free to ask Claude questions about a section in their instructions you don't understand, want more information about, and so on. The steps Claude will put forth are entirely optional, and of course some of them might be incorrect (sometimes AI gets things wrong). However Claude tends to really shine when it comes to technical items especially those involving coding and security.

### Simple Isolation with Personal VPN

A personal VPN (Virtual Private Network) can create an isolated network for a team member's computer that could be used for isolation if the Guest Network idea does not meet your needs. This has the added advantage of being mobile, in that if you take your computer to *any* network (free Wi-Fi at a coffee shop, hotel network, technical conference with Wi-Fi access for attendees, etc) you can isolate it.

For more information on a personal VPN, check out the Personal VPN page.

Similar to the guest network scenario above, when using a personal VPN you will not be able to access shared resources in your home like a printer.

### Advanced Isolation with DDWRT

The instructions are specific to DDWRT (granted a somewhat older and more technical technique), which is a popular but custom router firmware. If you don't use DDWRT, you can use the provided steps as a template and consult your router's manual to obtain a similar configuration. However, if your home router does not support setting up an isolated network, consider buying a router that is compatible with DDWRT or a similar custom firmware. If you need recommendations for DDWRT routers, you can find many buyer guides online:

- ProPrivacy guide
- List of supported DDWRT devices

1. **Backup config**. Before you start setting up your new work WiFi, you should save your current configuration so that you can restore it if necessary. To do this, go to tab *Administration* -> *Backup*.
1. **Create your work WiFi.** On tab *Wireless* -> *Basic Settings*, go to section *Virtual Interface* and click the *Add Virtual AP* button. Choose a name for your work WiFi and enter it in *Wireless Network Name (SSID)*.
1. **Advanced WiFi configuration.** Tick *Advanced Settings* to open up more configuration opens for our newly created WiFi. Set *Network Configuration* to *Unbridged*. Enable *Masquerade / NAT* and *Net Isolation* (this option creates a couple of firewall rules that blocks your work laptop from reaching your private network and vice versa). Assign an IP address, for example `172.16.2.1`, and set the subnet mask accordingly, usually `255.255.255.0`. Hit *Save* at the bottom of the page.
1. **Setup Security**. Next, we will set up encryption. Go to tab **Wireless Security** and go to the section that shows the name (SSID) of our newly created WiFi. Tick *WPA2 Personal*, *CCMP-128 (AES)* and enter the WiFi password into *WPA Shared Key*. Hit *Save*.
1. **Set up DHCP**. To automatically assign an IP address to devices on our new WiFi, we have to enable DHCP. Go to tab *Setup* -> *Networking*, scroll to section *DHCPD* at the bottom. Click *Add* and select the interface belonging to our new WiFi (most likely `ath0.1`) and hit *Save*.

That's it. If you search for nearby WiFi on your work laptop, our new WiFi should show up with the name you assigned.

Above steps are adapted from an existing guide.
