#!/usr/bin/env python3
"""
Interactive CLI for Onboarding New Users & Demo Preparation
Google Agent Assist + Genesys Cloud + Salesforce Service Cloud LWC Integration
"""

import os
import sys
import json
import subprocess
import shutil
import webbrowser

# ANSI Color Codes
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

DEFAULT_TARGET_ORG = "aa-scratch"
DEFAULT_QUEUE = "jblakey-agent-assist-queue"
DEFAULT_GROUP = "Agent Assist Dev"
DEFAULT_CONNECTOR_URL = "https://aa-ui-connector-v9x2-798656365078.us-central1.run.app"
DEFAULT_AUDIOHOOK_URL = "wss://aa-audiohook-v9x2-798656365078.us-central1.run.app/connect"
DEFAULT_GENESYS_ADMIN_URL = "https://apps.usw2.pure.cloud/#/admin"

def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")

def print_banner():
    print(f"{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║         Google Agent Assist + Genesys Cloud + Salesforce LWC          ║{RESET}")
    print(f"{CYAN}{BOLD}║                Demo User Onboarding & Environment CLI                 ║{RESET}")
    print(f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════════════════════════╝{RESET}\n")

def prompt_choice(prompt_text, default="y"):
    choice = input(f"{YELLOW}{prompt_text} [{default}]: {RESET}").strip().lower()
    if not choice:
        choice = default
    return choice

def run_sf_command(cmd_args, capture_output=False, check=True):
    cmd_str = " ".join(cmd_args)
    print(f"\n{DIM}Executing: {cmd_str}{RESET}")
    try:
        if capture_output:
            res = subprocess.run(cmd_args, capture_output=True, text=True, check=check)
            return res.stdout.strip(), res.stderr.strip()
        else:
            res = subprocess.run(cmd_args, check=check)
            return res.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error executing command ({e.returncode}): {cmd_str}{RESET}")
        if capture_output and e.stderr:
            print(f"{RED}{e.stderr}{RESET}")
        return None

def step_create_sf_user(org_alias=DEFAULT_TARGET_ORG):
    print(f"\n{BLUE}{BOLD}=== [Task 1] Create Salesforce Scratch Org User ==={RESET}")
    username = input(f"{YELLOW}Enter email/username for coworker [e.g. jsmith-demo@example.com]: {RESET}").strip()
    if not username:
        print(f"{RED}Username cannot be empty.{RESET}")
        return None
    
    first_name = input(f"{YELLOW}Enter First Name [e.g. John]: {RESET}").strip() or "Demo"
    last_name = input(f"{YELLOW}Enter Last Name [e.g. Smith]: {RESET}").strip() or "User"
    user_alias = input(f"{YELLOW}Enter local alias for this user [e.g. coworker-demo]: {RESET}").strip() or "coworker-demo"

    cmd = [
        "sf", "org", "create", "user",
        "--target-org", org_alias,
        "--set-alias", user_alias,
        "--set-unique-username",
        f"username={username}",
        f"email={username}",
        "profileName=System Administrator",
        f"FirstName={first_name}",
        f"LastName={last_name}",
        "generatepassword=true"
    ]

    conf = prompt_choice("Run Salesforce user creation command now?")
    if conf in ["y", "yes"]:
        success = run_sf_command(cmd, check=False)
        if not success:
            print(f"{RED}Failed to create user in scratch org. Please check error output above.{RESET}")
            return None
        
        # Get login credentials
        out, _ = run_sf_command(["sf", "org", "display", "user", "--target-org", user_alias, "--json"], capture_output=True, check=False)
        user_info = {}
        if out:
            try:
                data = json.loads(out)
                user_info = data.get("result", {})
            except Exception:
                pass

        # Generate frontdoor URL
        f_out, _ = run_sf_command(["sf", "org", "open", "--target-org", user_alias, "--url-only", "--json"], capture_output=True, check=False)
        login_url = ""
        if f_out:
            try:
                f_data = json.loads(f_out)
                login_url = f_data.get("result", {}).get("url", "")
            except Exception:
                pass

        actual_username = user_info.get("username", username)
        print(f"\n{GREEN}{BOLD}✓ User Provisioned Successfully in Scratch Org!{RESET}")
        print(f"  • {BOLD}Username:{RESET} {actual_username}")
        print(f"  • {BOLD}Password:{RESET} {user_info.get('password', '[Generated]')}")
        print(f"  • {BOLD}Instance URL:{RESET} {user_info.get('instanceUrl', 'https://test.salesforce.com')}")
        if login_url:
            print(f"  • {BOLD}Direct 1-Click Login URL:{RESET}\n    {CYAN}{login_url}{RESET}")
        
        return {
            "username": actual_username,
            "password": user_info.get("password", ""),
            "alias": user_alias,
            "login_url": login_url
        }
    return None

def step_assign_sf_permissions(user_alias=DEFAULT_TARGET_ORG):
    print(f"\n{BLUE}{BOLD}=== [Task 2] Assign Call Center & Omni-Channel Permissions ==={RESET}")
    print("This task configures Call Center softphone linkage and assigns the Omni-Channel presence access permission set.")
    
    target = input(f"{YELLOW}Enter target org/user alias [{user_alias}]: {RESET}").strip() or user_alias
    
    # 1. Call Center Script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cc_script = os.path.join(script_dir, "apex", "create_callcenter.apex")
    omni_script = os.path.join(script_dir, "apex", "setup_omnichannel.apex")
    
    conf = prompt_choice("Run Call Center assignment script (create_callcenter.apex)?")
    if conf in ["y", "yes"] and os.path.exists(cc_script):
        run_sf_command(["sf", "apex", "run", "--file", cc_script, "--target-org", target], check=False)
    
    conf = prompt_choice("Run Omni-Channel setup script (setup_omnichannel.apex)?")
    if conf in ["y", "yes"] and os.path.exists(omni_script):
        run_sf_command(["sf", "apex", "run", "--file", omni_script, "--target-org", target], check=False)

    print(f"\n{GREEN}{BOLD}✓ Salesforce CTI & Omni-Channel Assignments Completed!{RESET}")

def step_genesys_checklist():
    print(f"\n{BLUE}{BOLD}=== [Task 3] Genesys Cloud Admin Setup Guide ==={RESET}")
    print(f"Opening Genesys Cloud Admin Console in browser: {CYAN}{DEFAULT_GENESYS_ADMIN_URL}{RESET}\n")
    try:
        webbrowser.open(DEFAULT_GENESYS_ADMIN_URL)
    except Exception as e:
        print(f"{YELLOW}Note: Could not open browser automatically ({e}). Please open: {DEFAULT_GENESYS_ADMIN_URL}{RESET}\n")

    print("Perform these actions in the Genesys Cloud Admin Console (requires Admin access):\n")
    print(f"1. {BOLD}Create / Verify User Account:{RESET}")
    print("   • Go to: Admin > Directory > People and Permissions > Users > Add User")
    print(f"   • Link: {CYAN}https://apps.usw2.pure.cloud/#/admin/directory/users{RESET}")
    print("   • Set name and email for your coworker.")
    input(f"{DIM}[Press Enter once user is created in Genesys]{RESET}")
    
    print(f"\n2. {BOLD}Assign Required Roles:{RESET}")
    print("   • Edit User > Roles tab:")
    print(f"     - {GREEN}Agent{RESET} (or Contact Center Agent)")
    print(f"     - {GREEN}Communicate - User{RESET} (or PureCloud User)")
    print("   • (Grants Telephony, Call Accept/Make, Queue Join permissions)")
    input(f"{DIM}[Press Enter once roles are assigned]{RESET}")

    print(f"\n3. {BOLD}Assign WebRTC Phone:{RESET}")
    print("   • Go to: Admin > Telephony > Phone Management (or edit User > Phone tab)")
    print(f"   • Link: {CYAN}https://apps.usw2.pure.cloud/#/admin/telephony/phones{RESET}")
    print("   • Assign a WebRTC Phone (e.g. 'Genesys Cloud WebRTC Phone').")
    print("   • This allows softphone audio streaming in Chrome without a physical phone.")
    input(f"{DIM}[Press Enter once WebRTC Phone is assigned]{RESET}")

    print(f"\n4. {BOLD}Add User to Voice Queue & Group:{RESET}")
    print(f"   • Go to: Admin > Contact Center > Queues > {BOLD}{DEFAULT_QUEUE}{RESET} > Members")
    print(f"   • Link: {CYAN}https://apps.usw2.pure.cloud/#/admin/directory/queues{RESET}")
    print("   • Click '+ Add User' and select your coworker.")
    print(f"   • Go to: Admin > Directory > Groups > {BOLD}{DEFAULT_GROUP}{RESET} > Members > Add User.")
    input(f"{DIM}[Press Enter once queue and group memberships are saved]{RESET}")

    print(f"\n{GREEN}{BOLD}✓ Genesys Cloud Provisioning Checklist Completed!{RESET}")

def get_scratch_users(org_alias=DEFAULT_TARGET_ORG):
    out, _ = run_sf_command(["sf", "org", "list", "users", "--target-org", org_alias, "--json"], capture_output=True, check=False)
    if out:
        try:
            data = json.loads(out)
            return data.get("result", [])
        except Exception:
            pass
    return []

def get_user_credentials(user_alias_or_username):
    # Fetch password
    pass_out, _ = run_sf_command(["sf", "org", "auth", "show-user-password", "--target-org", user_alias_or_username, "--json"], capture_output=True, check=False)
    password = ""
    if pass_out:
        try:
            p_data = json.loads(pass_out)
            password = p_data.get("result", {}).get("password", "")
        except Exception:
            pass
            
    # Fetch frontdoor login url
    f_out, _ = run_sf_command(["sf", "org", "open", "--target-org", user_alias_or_username, "--url-only", "--json"], capture_output=True, check=False)
    login_url = ""
    if f_out:
        try:
            f_data = json.loads(f_out)
            login_url = f_data.get("result", {}).get("url", "")
        except Exception:
            pass
            
    return {"password": password, "login_url": login_url}

def step_coworker_instructions(user_info=None):
    print(f"\n{BLUE}{BOLD}=== [Task 4] Generate Coworker Onboarding & Demo Runbook ==={RESET}")
    
    if not user_info:
        users = get_scratch_users()
        if users:
            print("Found existing users in scratch org:")
            for i, u in enumerate(users, 1):
                alias_str = f" ({BOLD}{u.get('alias')}{RESET})" if u.get('alias') else ""
                print(f"  {CYAN}{i}.{RESET} {u.get('username')}{alias_str}")
            print(f"  {CYAN}m.{RESET} Enter credentials manually\n")
            
            sel = input(f"{YELLOW}Select a user to auto-fetch credentials [1-{len(users)}, or m]: {RESET}").strip().lower()
            if sel.isdigit() and 1 <= int(sel) <= len(users):
                chosen = users[int(sel) - 1]
                target_id = chosen.get("alias") or chosen.get("username")
                print(f"{DIM}Retrieving password and 1-click login URL for {target_id}...{RESET}")
                creds = get_user_credentials(target_id)
                user_info = {
                    "username": chosen.get("username"),
                    "password": creds.get("password"),
                    "login_url": creds.get("login_url"),
                    "alias": chosen.get("alias")
                }
        if not user_info:
            user_info = {}
            user_info["username"] = input(f"{YELLOW}Salesforce Username: {RESET}").strip()
            user_info["password"] = input(f"{YELLOW}Salesforce Password: {RESET}").strip()
            user_info["login_url"] = input(f"{YELLOW}Direct 1-Click Login URL (optional): {RESET}").strip()

    runbook = f"""
# Google Agent Assist & Genesys Cloud Demo Runbook (For Tester / Presenter)

## 1. Salesforce Login
- **URL**: {user_info.get('login_url') or 'https://test.salesforce.com'}
- **Username**: `{user_info.get('username')}`
- **Password**: `{user_info.get('password', '[Refer to admin]')}`
- **App**: Open **Service Console** from the App Launcher (9 dots in top-left).

## 2. Browser Pop-up & Microphone Settings (CRITICAL)
1. In Chrome address bar, click the **Site Settings / Lock / Tune** icon.
2. Ensure **Pop-ups and redirects** is set to **Always allow** for:
   - `https://*.scratch.lightning.force.com` (or `https://*.salesforce.com`)
   - `https://*.pure.cloud` (or `https://*.mypurecloud.com`)
3. Ensure **Microphone** permission is set to **Allow**.

## 3. Genesys CTI Softphone Login
1. In the bottom utility bar of Service Console, click **Genesys CTI Softphone**.
2. Log in with your Genesys Cloud credentials.
3. In the top-right corner of the softphone panel, toggle your status to **On Queue**.
4. Verify the queue (`{DEFAULT_QUEUE}`) toggle switch is enabled.

## 4. Executing the Test Call
1. Dial the inbound demo phone number.
2. The softphone will ring -> accept call -> Salesforce auto-screen-pops the Case record.
3. Google Agent Assist (`agentAssistContainerModule`) on the right sidebar will automatically bind the session within 1–3 seconds.
4. Speak customer/agent dialog to see real-time transcripts, smart replies, and conversation summaries.

## 5. After Call Work (ACW)
- After hanging up, **select a wrap-up code and complete ACW** in the CTI softphone so your status returns to **On Queue** for subsequent calls.
"""
    output_path = os.path.expanduser("~/COWORKER_DEMO_RUNBOOK.md")
    with open(output_path, "w") as f:
        f.write(runbook.strip())

    print(f"\n{GREEN}{BOLD}✓ Coworker Demo Runbook Generated!{RESET}")
    print(f"Saved locally to: {CYAN}{output_path}{RESET}\n")
    print(f"{DIM}--- Runbook Preview ---{RESET}")
    print(runbook)

def step_health_check():
    print(f"\n{BLUE}{BOLD}=== [Task 5] System Health & Readiness Diagnostics ==={RESET}")
    
    # Check SF CLI
    sf_version, _ = run_sf_command(["sf", "--version"], capture_output=True, check=False)
    if sf_version:
        print(f"  • {GREEN}✓ SF CLI:{RESET} {sf_version}")
    else:
        print(f"  • {RED}✗ SF CLI not found or errored.{RESET}")

    # Check Cloud Run UI Connector
    print(f"  • Checking UI Connector ({DEFAULT_CONNECTOR_URL})...")
    try:
        import urllib.request
        req = urllib.request.Request(DEFAULT_CONNECTOR_URL, headers={"User-Agent": "HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"    {GREEN}✓ UI Connector reachable (HTTP {resp.status}){RESET}")
    except Exception as e:
        print(f"    {YELLOW}! UI Connector response: {e}{RESET}")

    # Check active scratch orgs
    org_list, _ = run_sf_command(["sf", "org", "list", "--json"], capture_output=True, check=False)
    if org_list:
        try:
            data = json.loads(org_list)
            scratch_orgs = data.get("result", {}).get("scratchOrgs", [])
            print(f"  • {GREEN}✓ Active Scratch Orgs ({len(scratch_orgs)} found):{RESET}")
            for o in scratch_orgs:
                alias = o.get("alias", "no-alias")
                user = o.get("username", "")
                exp = o.get("expirationDate", "")
                print(f"    - [{alias}] {user} (Expires: {exp})")
        except Exception:
            pass

def interactive_wizard():
    clear_screen()
    print_banner()
    print(f"{BOLD}Starting Guided Onboarding Wizard...{RESET}\n")
    
    user_info = step_create_sf_user()
    step_assign_sf_permissions(user_alias=user_info.get("alias", DEFAULT_TARGET_ORG) if user_info else DEFAULT_TARGET_ORG)
    step_genesys_checklist()
    step_coworker_instructions(user_info)
    
    print(f"\n{GREEN}{BOLD}═══════════════════════════════════════════════════════════════════════{RESET}")
    print(f"{GREEN}{BOLD}       🎉 All Onboarding Tasks Successfully Completed!                 {RESET}")
    print(f"{GREEN}{BOLD}═══════════════════════════════════════════════════════════════════════{RESET}\n")

def main_menu():
    latest_user_info = None
    while True:
        clear_screen()
        print_banner()
        print(f"{BOLD}Select a task to perform:{RESET}\n")
        print(f"  {CYAN}1.{RESET} 🚀 {BOLD}Run Full Step-by-Step Onboarding Wizard{RESET}")
        print(f"  {CYAN}2.{RESET} 👤 Create Salesforce Scratch Org User & Credentials")
        print(f"  {CYAN}3.{RESET} ⚙️  Assign CTI Call Center & Omni-Channel Permissions")
        print(f"  {CYAN}4.{RESET} 📞 Genesys Cloud Roles, WebRTC Phone & Queue Setup Guide")
        print(f"  {CYAN}5.{RESET} 📄 Generate Coworker Demo Runbook (Markdown / Slack copy)")
        print(f"  {CYAN}6.{RESET} 🩺 Run System Diagnostics & Health Check")
        print(f"  {CYAN}q.{RESET} Exit\n")
        
        choice = input(f"{YELLOW}Enter your choice [1-6, q]: {RESET}").strip().lower()
        
        if choice == "1":
            interactive_wizard()
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice == "2":
            latest_user_info = step_create_sf_user()
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice == "3":
            alias = latest_user_info.get("alias", DEFAULT_TARGET_ORG) if latest_user_info else DEFAULT_TARGET_ORG
            step_assign_sf_permissions(alias)
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice == "4":
            step_genesys_checklist()
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice == "5":
            step_coworker_instructions(latest_user_info)
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice == "6":
            step_health_check()
            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")
        elif choice in ["q", "quit", "exit"]:
            print(f"\n{CYAN}Goodbye!{RESET}\n")
            break
        else:
            print(f"{RED}Invalid option.{RESET}")

if __name__ == "__main__":
    main_menu()
