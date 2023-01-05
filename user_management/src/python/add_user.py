import flywheel
import logging
import os
from typing import List
import sys

logging.basicConfig(level="DEBUG")
log = logging.getLogger("ADDUSER")


# Initialize the client:
fw = flywheel.Client(os.environ["NACC_API"], root=True)

# Specify the list of users emails to be added or removed form projects
USERS = [
			"zstark@washington.edu",
			"chandhn@washington.edu"
		]

# Specify the project labels to add them to
# Format should be in flywheel paths: <group_id>/<project_label>
# Or just put "ALL" to preform the operations on all projects
PROJECTS = [
				"ALL"
			]

# Specify the operation to perform.  "ADD" or "REMOVE"
OPERATION = "ADD"

# Specify the role we want to add.  Options are:
# 	- "admin" 		- project admin
# 	- "read-write" 	- project read/write
#	- "read-only"	- project read only
ROLE = "admin"

DRYRUN = True


###########################
# Flywheel Role Jargon    #
###########################
# First get the flywheel roles and identify which is admin, which is rw, and which is ro

fw_roles = fw.get_all_roles()
roles_labels = ['admin','read-only','read-write']
ROLE_IDS = {roi.label:roi.id for roi in fw_roles if roi.label in roles_labels}
if ROLE not in ROLE_IDS:
	log.error(f"Role {ROLE} not found in {[r.label for r in fw_roles]}")
	sys.exit()




def get_users(email_list: List[str]=USERS)->List[flywheel.User]:
	log.info('getting users from email')
	users = []

	for u in USERS:
		try:
			user = fw.get_user(u)
		except Exception:
			log.warning(f"Unable to get user {u}")
			continue

		users.append(user)

	return users


def create_user_role(user: flywheel.User, role: str) -> flywheel.models.roles_role_assignment.RolesRoleAssignment:
	log.info(f"creating role for {user.id}")
	# I know, I don't get it either...There's probably an easier way
	user_role = flywheel.models.roles_role_assignment.RolesRoleAssignment(id=user.id, role_ids=[role])
	return user_role



def addremove_user_to_project(project: flywheel.Project, roles: List[flywheel.models.roles_role_assignment.RolesRoleAssignment]) -> None:
	log.debug(f"processing {project.label}")
	for role in roles:
		if OPERATION == "ADD":
			log.info(f'Adding {role.id} as {role.role_ids} to {project.label}')
			permissions = project.permissions
			permission = [p for p in permissions if p.id==role.id]
			if permission:
				log.info(f'Permissions exist for {role.id}, ammending')
				permission=permission[0]
				existing_role=permission.role_ids
				existing_role.append(role.id)
				if DRYRUN:
					continue
				project.update_permission(user_id=role.id,permission={'role_ids':existing_role})
				continue

			if DRYRUN:
				continue
			project.add_permission(role)
			continue


		elif OPERATION == "REMOVE":
			log.info(f'Removing role {role.id} from {project.label}')
			if DRYRUN:
				continue

			try:
				project.remove_permission(user_id=role.id)
			except Exception as e:
				log.exception(e)

			continue


def get_projects():

	if PROJECTS == ["ALL"]:
		projects = fw.projects()
		return projects

	else:
		projects=[]
		for p in PROJECTS:
			projects.append(fw.lookup(p))

		return get_projects





if __name__ == "__main__":


	user_list = get_users()
	project_list = get_projects()

	user_roles = []
	for user in user_list:
		user_role = create_user_role(user, ROLE_IDS[ROLE])
		user_roles.append(user_role)

	for project in project_list:
		addremove_user_to_project(project, user_roles)




