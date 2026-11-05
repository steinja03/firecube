# Read-only Home API inspection after the accessibility trial

## What the complete result proved

The user's second trial receipt confirms installation, successful pause control,
a service-list write attempt, failed readback and verified rollback. Both original
accessibility settings were restored: service list empty, enabled flag 0. The
bridge APK remains installed and paused. There was no Home-redirection test.

The helper did not record the failed readback's actual value, so the exact cause
(rejection, normalization, vendor sanitization or a later reset) is not established.
Future receipts now retain expected and actual readbacks before reporting failure.
Do not equate this result with a proved missing WRITE_SECURE_SETTINGS permission.
The shell package report lists WRITE_SECURE_SETTINGS and SET_PREFERRED_APPLICATIONS,
but not CHANGE_COMPONENT_ENABLED_STATE among its grants.

## Why another inspection is justified

In Android 5.1's upstream source, HomeSettings uses replacePreferredActivity.
The package service checks SET_PREFERRED_APPLICATIONS for that operation, while
app enabled-state changes check CHANGE_COMPONENT_ENABLED_STATE. Thus the observed
disable failure and missing pm command do not rule out a distinct preferred-Home
interface. Amazon can modify that interface or physical Home handling; a listed
permission or method alone proves neither permission to write nor functional Home.

Sources inspected:
- https://github.com/aosp-mirror/platform_packages_apps_settings/blob/android-5.1.1_r38/src/com/android/settings/HomeSettings.java
- https://github.com/aosp-mirror/platform_frameworks_base/blob/android-5.1.1_r38/core/java/android/content/pm/IPackageManager.aidl
- https://github.com/aosp-mirror/platform_frameworks_base/blob/android-5.1.1_r38/services/core/java/com/android/server/pm/PackageManagerService.java

## What this inspector does

Run-Home-Inspector.cmd starts a Python 3.13 script. It asks for official ADB and
the connected Stick identifier, checks tank/API 22, reads existing accessibility
values, copies a known-hash Android DEX container to /data/local/tmp, pulls it back
and verifies the transfer hash, then runs it with app_process as ordinary shell
UID 2000. The APK is a code container; it is NOT installed as an application.
Only that temporary inspector file is written on the device. It can be removed
later; it requests no accessibility activation, root or firmware operation.

The DEX entry point accepts only inspect mode. Its package-manager gateway allows
only getHomeActivities, getPreferredActivities, resolveIntent and checkUidPermission.
It can list interface signatures, but it rejects calls to setters even if exposed.
The helper reports candidates, preferred and resolved Home components, existing
Home-only preferred filters and three effective permission checks. It does not
collect non-Home URL/application preferences, press Home, disable apps or call any
package-manager mutation. Both accessibility settings are read again afterward.
No reflection result is presented as proof a future write will be allowed.

## Windows steps

1. Extract the entire inspector ZIP to a writable folder.
2. Double-click Run-Home-Inspector.cmd.
3. Enter official adb.exe (Enter accepts the previous Downloads default) and the
   current device identifier, such as 192.168.50.39:5555.
4. Upload the resulting home-inspection ZIP after reviewing endpoint/package data.

No extra Python packages, launcher update or app install is required. Keep the
Home Bridge paused; do not rerun the write trial or restore it again after the
already-verified rollback. If the inspector fails, the ZIP records the failure
without turning it into a compatibility verdict. Source/build/unit tests cannot
substitute for this vendor-runtime result.
