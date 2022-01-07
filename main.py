import os
import hashlib
from qrme import *
from database import *
from PIL import Image
from flask_cors import CORS
from datetime import datetime
from flask_cors.decorator import cross_origin
from flask import Flask, render_template, request, redirect, jsonify, send_file

db = DataBase(path=os.path.join(os.getcwd(), "db"), filename="b52.db")
db.create_table(name="users",
                labels={"id": DBType.TEXT,
                        "user_name": DBType.TEXT,
                        "first_name": DBType.TEXT,
                        "second_name": DBType.TEXT,
                        "patronymic": DBType.TEXT,
                        "company_id": DBType.TEXT,
                        "tasks": DBType.TEXT,
                        "categories": DBType.TEXT,
                        "phone": DBType.TEXT,
                        "email": DBType.TEXT,
                        "password": DBType.TEXT},
                primary_key="id")

db.create_table(name="company",
                labels={"id": DBType.TEXT,
                        "admin": DBType.TEXT,
                        "company_name": DBType.TEXT,
                        "employees": DBType.TEXT,
                        "locations": DBType.TEXT,
                        "tasks": DBType.TEXT,
                        "categories": DBType.TEXT,
                        "licenses": DBType.INTEGER},
                primary_key="id")

db.create_table(name="task",
                labels={"id": DBType.TEXT,
                        "description": DBType.TEXT,
                        "location": DBType.TEXT,
                        "status": DBType.TEXT,
                        "category": DBType.TEXT,
                        "executor": DBType.TEXT,
                        "create_at": DBType.TEXT},
                primary_key="id")

db.create_table(name="location",
                labels={"id": DBType.TEXT,
                        "name": DBType.TEXT,
                        "floor": DBType.INTEGER,
                        "room": DBType.TEXT,
                        "url": DBType.TEXT},
                primary_key="id")

db.create_table(name="category",
                labels={"id": DBType.TEXT,
                        "name": DBType.TEXT})

app = Flask(__name__)
CORS(app)
tokens = {}
hostname = "http://127.0.0.1:5000/"


# =========================================================USER=========================================================
@app.route('/api/login', methods=['POST'])
@cross_origin()
def user_login() -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if get_hash(my_string=api_json['email']) not in db.get_table("users").get_all_UIDs():
        return jsonify(message="There is no such user!"), 401
    user = db.get_table("users").get_row(key=get_hash(my_string=api_json['email']))
    if user["password"] != api_json['password']:
        return jsonify(message="Password is incorrect!"), 401
    token = user["id"] + get_hash(str(datetime.now()))
    tokens[token] = user["id"]
    return jsonify({"user": get_user(user_id=user["id"]).get_json(),
                    "token": token})


@app.route('/api/registerUser', methods=['POST'])
@cross_origin()
def register_user() -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    user_id = get_hash(api_json['email'])
    company_id = get_hash(api_json['company_name'])
    if user_id in db.get_table("users").get_all_UIDs():
        return jsonify(message='User already exist!'), 401
    if "@" not in api_json['email']:
        return jsonify(message='The email must contain the "@" symbol!'), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        db_add_company(company_id=company_id,
                       admin=user_id,
                       company_name=api_json['company_name'],
                       employees=user_id,
                       locations="",
                       tasks="",
                       categories="",
                       licenses=20)
    else:
        employees = str(db.get_table("company").get_from_cell(key=company_id, column_name="employees")).split(",")
        db.get_table("company").set_to_cell(key=company_id, column_name="employees",
                                            new_value=",".join(list(filter(None, employees + [user_id]))))
    db_add_user(user_id=user_id,
                user_name=api_json['first_name'],
                first_name=api_json['first_name'],
                second_name=api_json['second_name'],
                patronymic=api_json['patronymic'],
                company_id=company_id,
                tasks="",
                categories="",
                phone=api_json['phone'],
                email=api_json['email'],
                password=api_json['password'])
    add_location(company_id=company_id,
                 name="Example of name",
                 floor="1",
                 room="1")
    token = user_id + get_hash(str(datetime.now()))
    tokens[token] = user_id
    return jsonify({"user": get_user(user_id=user_id).get_json(),
                    "token": token})


@app.route('/api/user/<string:user_id>', methods=['GET'])
@cross_origin()
def get_user(user_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if user_id not in db.get_table("users").get_all_UIDs():
        return jsonify(message='User not founded!'), 401
    user = db.get_table("users").get_row(user_id)
    company = db.get_table("company").get_row(user['company_id'])
    return jsonify({"id": user["id"],
                    "username": user["user_name"],
                    "first_name": user["first_name"],
                    "second_name": user["second_name"],
                    "patronymic": user["patronymic"],
                    "phone": user["phone"],
                    "categories": [get_company_category(company['id'], category_id).get_json()
                                   for category_id in list(filter(None, user['categories'].split(",")))],
                    "user_role": "ADMIN" if user["id"] == company["admin"] else "EMPLOYEE",
                    "company": {"id": user['company_id'],
                                "name": company["company_name"],
                                "licenses": company["licenses"]}})


@app.route('/api/user/<string:user_id>/changePassword', methods=['POST'])
@cross_origin()
def change_password(user_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if user_id not in db.get_table("users").get_all_UIDs():
        return jsonify(message='User not founded!'), 401
    if api_json['password'] != db.get_table("users").get_row(key=user_id)["password"]:
        return jsonify({"success": False})
    db.get_table("users").set_to_cell(key=user_id,
                                      column_name="password",
                                      new_value=request.args.get('new_password'))
    return jsonify(success=True)


def db_add_user(user_id: str, user_name: str, first_name: str, second_name: str, patronymic: str,
                company_id: str, tasks: str, categories: str, phone: str, email: str, password: str) -> None:
    db.get_table("users").add_row(row=[user_id, user_name, first_name, second_name, patronymic,
                                       company_id, tasks, categories, phone, email, password])


def get_user_short_name(user_id: str) -> str:
    user = db.get_table("users").get_row(key=user_id)
    return f"{user['second_name']} {user['first_name'][0].upper()}.{user['patronymic'][0].upper()}."


# =========================================================COMPANY======================================================
@app.route('/api/company/<string:company_id>', methods=['GET'])
@cross_origin()
def get_company_info(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    company = db.get_table("company").get_row(key=company_id)
    return jsonify({"id": company["id"],
                    "name": company["company_name"],
                    "licenses": company["licenses"]})


@app.route('/api/company/<string:company_id>', methods=['PATCH'])
@cross_origin()
def change_company_info(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    db.get_table("company").set_to_cell(key=company_id, column_name="company_name", new_value=api_json['name'])
    db.get_table("company").set_to_cell(key=company_id, column_name="licenses", new_value=api_json['licenses'])
    return jsonify(success=True)


@app.route('/api/company/<string:company_id>/employees', methods=['GET'])
@cross_origin()
def get_company_employees(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    items = []
    for employ in db.get_table("company").get_row(key=company_id)['employees'].split(","):
        try:
            user = db.get_table("users").get_row(key=employ)
            items.append({"id": user["id"], "full_name": get_user_short_name(user["id"])})
        except:
            pass
    return jsonify({"items": items})


@app.route('/api/company/<string:company_id>/registerEmployee', methods=['POST'])
@cross_origin()
def company_register_employee(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if get_hash(api_json['email']) in db.get_table("users").get_all_UIDs():
        return jsonify(message='This user already exist!'), 401
    company = db.get_table("company").get_row(key=company_id)
    if get_hash(api_json['email']) in company['employees'].split(","):
        return jsonify(message="This user already exist"), 401
    db_add_user(user_id=get_hash(api_json['email']),
                user_name=api_json['first_name'],
                first_name=api_json['first_name'],
                second_name=api_json['second_name'],
                patronymic=api_json['patronymic'],
                company_id=company_id,
                tasks="",
                categories=",".join(list(filter(None, api_json['categories']))),
                phone="8 (000) 000-00-00",
                email=api_json['email'],
                password=get_hash(api_json['first_name']))
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name="employees",
                                        new_value=",".join(list(filter(None, company['employees'].split(",") +
                                                                       [get_hash(api_json['email'])]))))
    return jsonify({"id": get_hash(api_json['email']),
                    "email": api_json['email'],
                    "first_name": api_json['first_name'],
                    "second_name": api_json['second_name'],
                    "patronymic": api_json['patronymic'],
                    "categories": [get_company_category(company_id, category_id).get_json()
                                   for category_id in list(filter(None, api_json['categories']))],
                    "password": get_hash(api_json['first_name'])})


@app.route('/api/company/<string:company_id>/employee/<string:user_id>', methods=['PATCH'])
@cross_origin()
def company_chenge_employee(company_id: str, user_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if user_id not in db.get_table("users").get_all_UIDs():
        return jsonify(message='User not founded!'), 401
    for field in ["first_name", "second_name", "patronymic", "phone"]:
        db.get_table("users").set_to_cell(key=user_id, column_name=field, new_value=api_json[field])
    db.get_table("users").set_to_cell(key=user_id, column_name="categories",
                                      new_value=",".join(list(filter(None, api_json['categories']))))
    return jsonify(success=True)


@app.route('/api/company/<string:company_id>/employee/<string:user_id>', methods=['DELETE'])
@cross_origin()
def company_delete_employee(company_id: str, user_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if user_id not in db.get_table("users").get_all_UIDs():
        return jsonify(message='User not founded!'), 401
    employees = db.get_table("company").get_row(key=company_id)['employees'].split(",")
    if user_id not in employees:
        return jsonify(message='User not founded in this company!'), 401
    employees.remove(user_id)
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name="employees",
                                        new_value=",".join(list(filter(None, employees))))
    db.get_table("users").delete_row(key=user_id)
    return jsonify(success=True)


def db_add_company(company_id: str, admin: str, company_name: str,
                   employees: str, locations: str, tasks: str, categories: str, licenses: int) -> None:
    db.get_table("company").add_row(row=[company_id, admin, company_name, employees,
                                         locations, tasks, categories, licenses])


# ========================================================TASKS=========================================================
@app.route('/api/company/<string:company_id>/task', methods=['POST'])
@cross_origin()
def create_company_task(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    task_id = f"{company_id}{get_hash(str(datetime.now()))}"
    db_add_task(task_id=task_id,
                description=api_json['description'],
                location=api_json['location'],
                status="OPEN",
                category=api_json['category'],
                executor="",
                create_at=datetime.now().strftime("%Y-%m-%d"))
    tasks = db.get_table("company").get_from_cell(key=company_id, column_name='tasks').split(",")
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name='tasks',
                                        new_value=",".join(list(filter(None, tasks + [task_id]))))
    return get_company_task(company_id, task_id)


@app.route('/api/company/<string:company_id>/task/<string:task_id>', methods=['GET'])
@cross_origin()
def get_company_task(company_id: str, task_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("task").get_all_UIDs():
        return jsonify(message='Task not founded!'), 401
    if task_id not in db.get_table("company").get_row(key=company_id)['tasks'].split(","):
        return jsonify(message='Task not founded in this company!'), 401
    task = db.get_table("task").get_row(key=task_id)

    return jsonify({"id": task['id'],
                    "description": task['description'],
                    "location": {"id": task['location'],
                                 "name": db.get_table("location").get_row(key=task['location'])['name']}
                    if task['location'] != "" else None,
                    "status": task['status'],
                    "category": {"id": task["category"],
                                 "name": db.get_table('category').get_from_cell(task['category'], "name")}
                    if task['category'] != "" else None,
                    "executor": {"id": task["executor"],
                                 "full_name": get_user_short_name(task["executor"])}
                    if task["executor"] != "" else None,
                    "create_at": task['create_at']})


@app.route('/api/company/<string:company_id>/task/<string:task_id>', methods=['PATCH'])
@cross_origin()
def set_company_task(company_id: str, task_id: str) -> jsonify:
    api_json = request.get_json()
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("task").get_all_UIDs():
        return jsonify(message='Task not founded!'), 401
    print()
    db.get_table("task").set_to_cell(key=task_id, column_name="description", new_value=api_json['description'])
    db.get_table("task").set_to_cell(key=task_id, column_name="status", new_value=api_json['status'])
    db.get_table("task").set_to_cell(key=task_id, column_name="create_at", new_value=api_json['create_at'])
    db.get_table("task").set_to_cell(key=task_id,
                                     column_name="location",
                                     new_value=api_json["location"]['id'] if api_json["location"] is not None else "")
    db.get_table("task").set_to_cell(key=task_id,
                                     column_name="category",
                                     new_value=api_json["category"]['id'] if api_json["category"] is not None else "")
    db.get_table("task").set_to_cell(key=task_id,
                                     column_name="location",
                                     new_value=api_json["executor"]['id'] if api_json["executor"] is not None else "")
    return get_company_task(company_id=company_id, task_id=task_id).get_json()


@app.route('/api/company/<string:company_id>/task/<string:task_id>/addExecutor', methods=['POST'])
@cross_origin()
def company_task_add_executor(company_id: str, task_id: str) -> jsonify:
    api_json = request.get_json()
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("task").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("company").get_row(key=company_id)['tasks'].split(","):
        return jsonify(message='Task not founded in this company!'), 401
    if task_id in db.get_table("users").get_row(key=api_json['user_id'])['tasks'].split(","):
        return jsonify(message='The user has already been assigned responsibility for this task!'), 401
    executors = db.get_table("task").get_from_cell(key=task_id, column_name="executor").split(",")
    db.get_table("task").set_to_cell(key=task_id,
                                     column_name="executor",
                                     new_value=",".join(list(filter(None, executors + [api_json['user_id']]))))
    user_tasks = db.get_table("users").get_from_cell(key=api_json['user_id'],
                                                     column_name="tasks").split(",")
    db.get_table("users").set_to_cell(key=api_json['user_id'],
                                      column_name="tasks",
                                      new_value=",".join(list(filter(None, user_tasks + [task_id]))))
    return get_company_task(company_id=company_id, task_id=task_id)


@app.route('/api/company/<string:company_id>/task/<string:task_id>/removeExecutor', methods=['POST'])
@cross_origin()
def company_task_remove_executor(company_id: str, task_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("task").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if task_id not in db.get_table("company").get_row(key=company_id)['tasks'].split(","):
        return jsonify(message='Task not founded in this company!'), 401
    if task_id not in db.get_table("users").get_row(key=api_json['user_id'])['tasks'].split(","):
        return jsonify(message='The user was not assigned responsibility for this task!'), 401
    executors: list = db.get_table("task").get_from_cell(key=task_id, column_name="executor").split(",")
    user_tasks = db.get_table("users").get_from_cell(key=api_json['user_id'], column_name="tasks").split(",")
    executors.remove(api_json['user_id'])
    user_tasks.remove(task_id)
    db.get_table("task").set_to_cell(key=task_id,
                                     column_name="executor",
                                     new_value=",".join(list(filter(None, executors))))
    db.get_table("users").set_to_cell(key=api_json['user_id'],
                                      column_name="tasks",
                                      new_value=",".join(list(filter(None, user_tasks))))
    return get_company_task(company_id=company_id, task_id=task_id).get_json()


@app.route('/api/company/<string:company_id>/tasks', methods=['GET'])
@cross_origin()
def get_company_tasks(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    company_tasks = []
    for task_id in list(filter(None, db.get_table("company").get_from_cell(company_id, "tasks").split(','))):
        try:
            this_task = get_company_task(company_id, task_id).get_json()
            if 'message' not in this_task:
                company_tasks.append(this_task)
        except:
            pass
    return jsonify({"items": company_tasks})


@app.route('/api/company/<string:company_id>/tasks/<string:user_id>', methods=['GET'])
@cross_origin()
def get_company_user_tasks(company_id: str, user_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if user_id not in db.get_table("users").get_all_UIDs():
        return jsonify(message='User not founded!'), 401
    user_tasks = []
    for task_id in list(filter(None, db.get_table("users").get_from_cell(user_id, "tasks").split(','))):
        try:
            this_task = get_company_task(company_id, task_id).get_json()
            if 'message' not in this_task:
                user_tasks.append(this_task)
        except:
            pass
    return jsonify({"items": user_tasks})


@app.route('/api/company/<string:company_id>/tasks/free', methods=['GET'])
@cross_origin()
def get_company_free_tasks(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    company_free_tasks = []
    for task_id in list(filter(None, db.get_table("company").get_from_cell(company_id, "tasks").split(','))):
        try:
            this_task = get_company_task(company_id, task_id).get_json()
            if 'message' not in this_task:
                if this_task['executor'] == "" or this_task['executor'] is None or \
                        this_task['executor']["id"] == "" or this_task['executor']["id"] is None:
                    company_free_tasks.append(this_task)
        except:
            pass
    return jsonify({"items": company_free_tasks})


def db_add_task(task_id: str, description: str, location: str,
                status: str, category: str, executor: str, create_at: str) -> None:
    db.get_table("task").add_row(row=[task_id, description, location, status, category, executor, create_at])


# ======================================================LOCATION========================================================
@app.route('/api/company/<string:company_id>/location', methods=['POST'])
@cross_origin()
def add_company_location(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    location_id = add_location(company_id, api_json['name'], api_json['floor'], api_json['room'])
    return get_company_location(company_id=company_id, location_id=location_id).get_json()


@app.route('/api/company/<string:company_id>/location/<string:location_id>', methods=['GET'])
@cross_origin()
def get_company_location(company_id: str, location_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if location_id not in db.get_table("company").get_row(key=company_id)['locations'].split(","):
        return jsonify(message='Location not founded!'), 401
    location = db.get_table("location").get_row(key=location_id)
    return jsonify({"id": location['id'],
                    "name": location['name'],
                    "floor": location['floor'],
                    "room": location['room'],
                    "url": location['url']})


@app.route('/api/company/<string:company_id>/location/<string:location_id>', methods=['PATCH'])
@cross_origin()
def change_company_location(company_id: str, location_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if location_id not in db.get_table("company").get_row(key=company_id)['locations'].split(","):
        return jsonify(message='Location not founded!'), 401
    for field in ["name", "floor", "room"]:
        db.get_table("location").set_to_cell(key=location_id, column_name=field, new_value=api_json[field])
    return jsonify(success=True)


@app.route('/api/company/<string:company_id>/locations', methods=['GET'])
@cross_origin()
def get_company_locations(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    locations = []
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    for location_id in db.get_table("company").get_row(key=company_id)['locations'].split(","):
        try:
            location = db.get_table("location").get_row(key=location_id)
            if 'message' not in location:
                locations.append({"id": location['id'],
                                  "name": location['name'],
                                  "floor": location['floor'],
                                  "room": location['room'],
                                  "url": location['url']})
        except:
            pass
    return jsonify(locations)


@app.route('/api/company/<string:company_id>/locations/grouped', methods=['GET'])
@cross_origin()
def get_company_grouped_locations(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    locations = {}
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    for location_id in list(filter(None, db.get_table("company").get_row(company_id)['locations'].split(","))):
        try:
            location = db.get_table("location").get_row(key=location_id)
            if 'message' not in location:
                if location['floor'] not in locations:
                    locations[location['floor']] = {"floor": location['floor'], "locations": []}
                locations[location['floor']]["locations"].append({"id": location['id'],
                                                                  "name": location['name'],
                                                                  "floor": location['floor'],
                                                                  "room": location['room'],
                                                                  "url": location['url']})
        except:
            pass
    return jsonify([locations[floor] for floor in sorted(locations.keys())])


def add_location(company_id: str, name: str, floor: str, room: str):
    company = db.get_table("company").get_row(key=company_id)
    location_id = company_id + get_hash(name) + get_hash(str(datetime.now()))
    if location_id in str(company['locations']).split(","):
        return jsonify(message="Locations already exist!"), 401
    create_qrcode(data=f"{hostname}#/company/{company_id}/location/{location_id}/createTask",
                  path_to_folder=os.path.join(os.getcwd(), "qrcodes"),
                  filename=f"{location_id}.png")
    db_add_location(location_id=location_id, name=name, floor=floor, room=room, url=f"/api/get_image/{location_id}.png")
    db.get_table('company').set_to_cell(key=company_id,
                                        column_name="locations",
                                        new_value=",".join(list(filter(None, company['locations'].split(",") +
                                                                       [location_id]))))
    return location_id


def db_add_location(location_id: str, name: str, floor: str, room: str, url: str) -> None:
    db.get_table("location").add_row(row=[location_id, name, floor, room, url])


# =======================================================CATEGORY=======================================================
@app.route('/api/company/<string:company_id>/category', methods=['POST'])
@cross_origin()
def set_company_category(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if f"{company_id}{get_hash(api_json['name'])}" in db.get_table("category").get_all_UIDs():
        return jsonify(message='This category is already exist!'), 401
    category_id = f"{company_id}{get_hash(api_json['name'])}"
    db_add_category(category_id=category_id, name=api_json['name'])
    company_categories = db.get_table("company").get_from_cell(key=company_id, column_name="categories").split(",")
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name="categories",
                                        new_value=",".join(list(filter(None, company_categories + [category_id]))))
    return jsonify({"id": category_id,
                    "name": api_json['name']})


@app.route('/api/company/<string:company_id>/category/<string:category_id>', methods=['GET'])
@cross_origin()
def get_company_category(company_id: str, category_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if category_id not in db.get_table("category").get_all_UIDs():
        return jsonify(message='Category not founded!'), 401
    return jsonify({"id": category_id,
                    "name": db.get_table("category").get_from_cell(key=category_id, column_name='name')})


@app.route('/api/company/<string:company_id>/category/<string:category_id>', methods=['PATCH'])
@cross_origin()
def change_company_category(company_id: str, category_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if category_id not in db.get_table("category").get_all_UIDs():
        return jsonify(message='Category not founded!'), 401
    db.get_table("category").set_to_cell(key=category_id, column_name='name', new_value=api_json['name'])
    return jsonify(success=True)


@app.route('/api/company/<string:company_id>/category/<string:category_id>', methods=['DELETE'])
@cross_origin()
def delete_company_category(company_id: str, category_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    if category_id not in db.get_table("category").get_all_UIDs():
        return jsonify(message='Category not founded!'), 401
    db.get_table("category").delete_row(key=category_id)
    try:
        categories = list(filter(None, db.get_table("company").get_from_cell(company_id, "categories").split(",")))
        if category_id in categories:
            categories.remove(category_id)
        db.get_table("company").set_to_cell(key=company_id, column_name="categories",
                                            new_value=",".join(list(filter(None, categories))))
    except:
        pass
    employees = db.get_table("company").get_from_cell(key=company_id, column_name="employees").split(",")
    for user_id in list(filter(None, employees)):
        user_categories = db.get_table("users").get_from_cell(key=user_id, column_name="categories").split(",")
        if category_id in user_categories:
            user_categories.remove(category_id)
        db.get_table("users").set_to_cell(key=user_id,
                                          column_name="categories",
                                          new_value=",".join(list(filter(None, user_categories))))

    for tasks_id in db.get_table("company").get_from_cell(key=company_id, column_name="tasks").split(","):
        db.get_table("task").set_to_cell(key=tasks_id, column_name="category", new_value="")
    return jsonify(success=True)


@app.route('/api/company/<string:company_id>/categories', methods=['GET'])
@cross_origin()
def get_company_categories(company_id: str) -> jsonify:
    if not check_api_key():
        return jsonify(message="Invalid API-KEY"), 401
    if company_id not in db.get_table("company").get_all_UIDs():
        return jsonify(message='Company not founded!'), 401
    categories = []
    for category_id in list(filter(None, db.get_table("company").get_from_cell(company_id, "categories").split(","))):
        try:
            category = get_company_category(company_id=company_id, category_id=category_id).get_json()
            if 'message' not in category:
                categories.append(category)
        except:
            pass
    return jsonify({"items": categories})


@app.route('/api/get_image/<string:image>.png', methods=['GET'])
@cross_origin()
def get_image(image: str) -> send_file:
    if f"{image}.png" not in os.listdir(os.path.join(os.getcwd(), "qrcodes")):
        return jsonify(message='Image not founded!'), 401
    return send_file(os.path.join(os.getcwd(), "qrcodes", f"{image}.png"), mimetype='image/png')


def db_add_category(category_id: str, name: str) -> None:
    db.get_table("category").add_row(row=[category_id, name])


def get_hash(my_string: str) -> str:
    """
    Этот метод на вход получает строку (в нашем часном случае - почту) и хэширует её
    :param my_string: Входная строка
    :return:
    """
    return hashlib.md5(my_string.encode()).hexdigest()


def check_api_key() -> bool:
    return request.headers.get('API-KEY') == "6kcDRDO!0B<;^MCM=bv'jyMO?(R)c/j0YIpx[>!Q*%kX;&99B^'xgQ_=}}R-5:fkme1"


if __name__ == '__main__':
    app.run(debug=True)
