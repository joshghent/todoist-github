import datetime

from dateutil.relativedelta import relativedelta

from todoist_github.clients import github, todoist
from todoist_github.utils import get_github_issue_details, get_github_task, get_issue
from todoist_github.utils.todoist import is_task_completed, issue_to_task_name


def get_relevant_todoist_tasks():
    todoist.items.sync()
    tasks = {}
    for task in todoist.items.all():
        github_task = get_github_task(task["content"])
        if github_task:
            tasks[github_task] = task
    return tasks


def assigned_issues():
    todoist_tasks = get_relevant_todoist_tasks()
    relevant_since = datetime.datetime.now() - relativedelta(
        weeks=30
    )  # TODO: Make this a sane number
    tasks_actioned = []
    me = github.get_user()
    for assigned_issue in me.get_issues(state="all", since=relevant_since):
        task = todoist_tasks.get(assigned_issue.html_url)
        if not task and assigned_issue.state == "open":
            task = todoist.items.add(issue_to_task_name(assigned_issue))
        if not task:
            continue
        tasks_actioned.append(task["id"])
        if assigned_issue == "closed" and not is_task_completed(task):
            print("completing", assigned_issue)
            task.complete()
        if is_task_completed(task):
            print("uncompleting task", assigned_issue)
            task.uncomplete()
        if task["content"] != issue_to_task_name(assigned_issue):
            print("updating issue name for", assigned_issue)
            task.update(content=issue_to_task_name(assigned_issue))
        if assigned_issue.milestone and assigned_issue.milestone.due_on:
            task.update(
                date_string=assigned_issue.milestone.due_on.strftime("%d/%m/%Y")
            )

    for task in todoist_tasks.values():
        if not is_task_completed(task) or task["id"] in tasks_actioned:
            continue
        issue_details = get_github_issue_details(task["content"])
        if not issue_details:
            continue
        org, repo, issue_number = issue_details
        issue = get_issue(me, org, repo, issue_number)
        me_assigned = me.login in {assignee.login for assignee in issue.assignees}
        if not me_assigned:
            print("Deleting", issue)
            task.delete()