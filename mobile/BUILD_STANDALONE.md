# Building a standalone iPhone app (no computer, no dev server)

This turns the Expo project into a real installable iPhone app. Once it's on your
phone via TestFlight, it runs on its own — **no computer, no `expo start`, no QR
code**. The **Comics · On-Device** feature works fully offline-of-your-PC (it
talks straight to ComicVine from the phone). The other buttons (Weekly Comics,
Movies, TV, etc.) still need your home server and will just show an error when
that server isn't reachable — nothing is removed, they simply stay server-based.

---

## Fastest option if you have a Mac (free, test it today)

This puts the **real standalone app** on your iPhone for **free** — no $99 account,
no cloud build. The catch: a free Apple ID signs apps for only **7 days**, after
which you re-plug to the Mac and re-run the command. Great for trying it now;
switch to TestFlight (below) when you want it permanent.

1. Install **Xcode** from the Mac App Store (once).
2. Plug your iPhone into the Mac with a cable; tap **Trust** on the phone.
3. In a terminal, in the `mobile/` folder:
   ```bash
   npx expo install react-native-webview   # if not already installed
   npx expo run:ios --device --configuration Release
   ```
   - Pick your iPhone from the device list.
   - If it asks for a signing team, open the generated `ios/` project in Xcode
     once, select your personal Apple ID team under Signing & Capabilities, then
     re-run the command.
4. First launch: on the phone go to **Settings → General → VPN & Device
   Management → [your Apple ID] → Trust**.

`--configuration Release` bundles the JavaScript into the app, so it runs with
**no Metro and no computer** — you can unplug and use it anywhere (for 7 days).

For a version that never expires and installs with no cable at all, use the
TestFlight route below.

---

## What you need first (permanent / TestFlight route)

1. **A free Expo account** — sign up at https://expo.dev.
2. **An Apple Developer account ($99/year)** — https://developer.apple.com/programs.
   This is an Apple requirement for putting your own app on a physical iPhone;
   there's no way around it for a no-computer install.

> The heavy build work happens in **Expo's cloud**, so you do **not** need a Mac
> or Xcode. You only need a terminal to *kick off* the first build.

---

## One-time setup (run in a terminal, in the `mobile/` folder)

You can do this on any computer once — yours, a friend's, or a free cloud shell.

```bash
npm install -g eas-cli          # the EAS command-line tool
eas login                       # log in with your Expo account
npx expo install react-native-webview   # pin the SDK-54 version (if not already)
eas init                        # links this project to your Expo account
eas build:configure             # confirms the iOS build config
```

`eas init` writes an `extra.eas.projectId` into `app.json` — commit that change.

---

## Build it in the cloud

```bash
eas build --platform ios --profile production
```

- The first time, EAS asks to handle your Apple signing credentials — say **yes**
  and log in with your Apple ID. EAS creates the certificates for you.
- The build runs on Expo's servers (~15–25 min). You get a link when it's done.

---

## Put it on your phone (TestFlight)

```bash
eas submit --platform ios --latest
```

Then, entirely on your iPhone:

1. Install **TestFlight** from the App Store.
2. Open the invite (Expo/App Store Connect emails it to your Apple ID).
3. Tap **Install**.

That's it — the app is now on your phone and runs with **no computer involved**.

---

## Using it

Open the app → **Comics · On-Device** → paste your free ComicVine API key
(https://comicvine.gamespot.com/api) → **Fetch this week** → pick favorites →
**Build slides** → **Save all to Photos** → post from Instagram.

---

## Rebuilding later without a computer

After the one-time setup above, future rebuilds can be triggered from Expo's
website (https://expo.dev → your project → Builds → **Build**) or via an EAS
Workflow on git push — so you won't need a terminal again. Ask and I can add the
push-triggered workflow.

---

## Notes

- **Bundle identifier** is `com.thewatchtower.app` (in `app.json`). Change it if
  you want a different one — just do it before the first build.
- **Free-account alternative:** without the $99 Apple account you can still make
  a build, but iOS only lets you install an unsigned app for 7 days and it needs
  a Mac + cable to sideload. TestFlight is the only no-computer route, and it
  needs the paid account.
