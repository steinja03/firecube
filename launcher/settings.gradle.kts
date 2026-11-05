pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "FirecubeLauncher"
include(":app")
include(":probe")
include(":bridge")
include(":inspect")
include(":homepref")
