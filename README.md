# AnonPost
Anonymous Image Board bot for Discord, inspired by 4chan/Futaba channel
Made for and by discord.gg/qatar - viist if u need help

---

# Guide
*You likely cannot afford a hosting service. In the rare case you can, scroll down for the selfhost guide.*
- Add the bot to your server with this link: https://discord.com/oauth2/authorize?client_id=1374149127725650083&permissions=8&integration_type=0&scope=bot
- Type `/setupanonch #channel` to setup anonymous posts. You will see a popup if setup correctly.
- You can disable posts at any time with `/removeanonch #channel`
- There are no logs. **Bans are handled by `/banuser` and require the posters unique ID**

---

# Selfhost Guide
**Modals do not accept file uploads, blame Discord's API.**
- AnonPost was written to be lightweight. It should be easy to edit.**Discord.py, Aiohttp and io**
- A button + modal combo is used on the frontend, while the backend uses bytesio to obfuscate links and handle ID's.
- A database is created to parse channels and bans.

If you are selfhosting, play around with the modals.
I recommend keeping URL's required if you want something remiscent of 4chan.
