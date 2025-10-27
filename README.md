# Odoo Add-ons Collection

Welcome to **odoo-addons** — a curated collection of add-on modules for Odoo, maintained by the team at KoderStory.

## 🧩 What’s included  
This repository contains a variety of modules (extensions, themes, utilities) that you can deploy with Odoo.  
Each module lives in its own folder and includes a `__manifest__.py` file specifying metadata, dependencies and license.

## 📦 Modules

Below is a quick overview of the modules shipped in this repository.  
> **Licensing note:** This is a mixed-license collection. Each module keeps its own license as declared in its `__manifest__.py` (AGPL-3 or LGPL-3 are common here). See each module folder for details.

| Module | Version | Description |
|---|---:|---|
| [**Automatic Backup** (`eqp_backup`)](https://github.com/koderstory/odoo-addons/tree/main/eqp_backup) | 18.0.1.0 | Automates Odoo DB/filestore backups (local/SFTP/GDrive/Dropbox), email notifications, retention policy. |
| [**Hide Any Menu User Wise** (`hide_menu_user`)](https://github.com/koderstory/odoo-addons/tree/main/hide_menu_user) | 18.0.2.0.0 | Hide specific menu items per user to simplify the UI. |
| [**Hide Powered by and Manage DB** (`hide_powered_by_and_manage_db`)](https://github.com/koderstory/odoo-addons/tree/main/hide_powered_by_and_manage_db) | 1.0 | Hides “Powered by” and “Manage Databases” links on the login page. |
| [**Hide User Menus (Top Right Corner)** (`hide_user_menus`)](https://github.com/koderstory/odoo-addons/tree/main/hide_user_menus) | 1.0 | Removes user-menu items (Documentation, Support, Shortcuts, etc.) for a cleaner interface. |
| [**Login As Any User** (`login_as_any_user`)](https://github.com/koderstory/odoo-addons/tree/main/login_as_any_user) | 18.0.1.0.0 | Admin can switch into any user account directly from the systray. |
| [**MuK Contacts** (`muk_contacts`)](https://github.com/koderstory/odoo-addons/tree/main/muk_contacts) | 18.0.1.0.3 | Enhancements for Contacts/partners with extra utilities and views. |
| [**MuK Product** (`muk_product`)](https://github.com/koderstory/odoo-addons/tree/main/muk_product) | 18.0.1.1.5 | Centralized product views accessible from the home menu; product utilities. |
| [**MuK AppsBar** (`muk_web_appsbar`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_appsbar) | 18.0.1.1.4 | Sidebar listing installed apps for faster navigation. |
| [**MuK Chatter** (`muk_web_chatter`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_chatter) | 18.0.1.2.3 | Improved chatter UI and option to choose its position. |
| [**MuK Colors** (`muk_web_colors`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_colors) | 18.0.1.0.6 | Theme color customization (light/dark variables). |
| [**MuK Dialog** (`muk_web_dialog`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_dialog) | 18.0.1.0.5 | Dialog QoL improvements (e.g., fullscreen) with user prefs. |
| [**MuK Backend Theme** (`muk_web_theme`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_theme) | 18.0.1.2.4 | Community backend theme, mobile-friendly, integrates with MuK web addons. |
| [**MuK Web Utils** (`muk_web_utils`)](https://github.com/koderstory/odoo-addons/tree/main/muk_web_utils) | 18.0.1.0.3 | Utility libraries/features for the web client used by other modules. |
| [**Password Visibility Toggle** (`password_visibility_toggle`)](https://github.com/koderstory/odoo-addons/tree/main/password_visibility_toggle) | 1.0 | Adds a show/hide password toggle on the login page. |
| [**Reports & Attachments Preview** (`report_attachment_preview`)](https://github.com/koderstory/odoo-addons/tree/main/report_attachment_preview) | 1.3 | Opens PDF reports and attachments in a new tab for quick preview. |


### 🔐 Licenses
This repository contains modules under **multiple licenses** (AGPL-3 and LGPL-3 among others).  
Each module’s license is declared in its `__manifest__.py`. Respect the terms of each module you use or distribute.

### 🚀 How to Install
1. Copy desired module folders to your Odoo `addons` path (or add this repository’s path to your `odoo.conf`).
2. Restart Odoo and update the Apps list.
3. Install the modules from the Apps UI.


## 📘 Licensing & Usage  
### Mixed-License Repository  
Because this collection mixes modules under different open-source licenses, **there is no single license** for the entire repo. Instead:

- Each module carries its own license (see the `license` field in its `__manifest__.py`).  
- Common licenses in the collection include:  
  - **GNU Affero General Public License v3.0 (AGPL-3.0)**  
  - **GNU Lesser General Public License v3.0 (LGPL-3.0) or earlier versions**  
- You are responsible for respecting the license terms of each module you use.
