import argparse
import getpass
from models.users import User

def get_username():
    return input("Enter your username: ")

def get_password():
    return getpass.getpass("Enter your password: ")

def get_password_confirmation():
    return getpass.getpass("Repeat your password: ")

def create_user(admin: bool):
    current_users = [u['username'] for u in User.list()]
    user = get_username()
    while user in current_users:
        print("User already exists. Try again.")
        user = get_username()

    password = get_password()
    password_confirmation = get_password_confirmation()
    while password != password_confirmation:
        print("Passwords do not match. Try again.")
        password = get_password()
        password_confirmation = get_password_confirmation()

    print(f"Creating user {user}...", end=" ")
    User.create(user, User.cypher(password), User.ADMIN if admin else User.ANNOTATOR)
    print("Done.")

def list_users():
    users = User.list()
    print("Users:")
    for u in users:
        print(f"-  {u['username']}")

def main():
    parser = argparse.ArgumentParser(description='Manage users for the backend.')
    parser.add_argument('action', choices=['create', 'list'], help='Action to perform.')
    parser.add_argument('--admin', action='store_true', help='Create an admin user.')

    args = parser.parse_args()

    if args.action == 'create':
        create_user(args.admin)
    elif args.action == 'list':
        list_users()

if __name__ == '__main__':
    main()
