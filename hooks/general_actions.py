# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk
import datetime
import os
import sys
import tempfile
import cPickle
import subprocess
import re

HookBaseClass = sgtk.get_hook_baseclass()


class GeneralActions(HookBaseClass):
    """
    General Shotgun Panel Actions that apply to all DCCs
    """

    def generate_actions(self, sg_data, actions, ui_area):
        """
        Returns a list of action instances for a particular object.
        The data returned from this hook will be used to populate the
        actions menu.

        The mapping between Shotgun objects and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the app
        has already established *which* actions are appropriate for this object.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        The ui_area parameter is a string and indicates where the item is to be shown.

        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.

        :param sg_data: Shotgun data dictionary with a set of standard fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption, group and description
        """
        app = self.parent
        app.log_debug(
            "Generate actions called for UI element %s. "
            "Actions: %s. SG Data: %s" % (ui_area, actions, sg_data)
        )

        action_instances = []

        if "assign_task" in actions:
            action_instances.append(
                {
                    "name": "assign_task",
                    "params": None,
                    "group": "Update task",
                    "caption": "Assign to yourself",
                    "description": "Assign this task to yourself.",
                }
            )

        if "task_to_ip" in actions:
            action_instances.append(
                {
                    "name": "task_to_ip",
                    "params": None,
                    "group": "Update task",
                    "caption": "Set to In Progress",
                    "description": "Set the task status to In Progress.",
                }
            )

        if "quicktime_clipboard" in actions:

            if sg_data.get("sg_path_to_movie"):
                # path to movie exists, so show the action
                action_instances.append(
                    {
                        "name": "quicktime_clipboard",
                        "params": None,
                        "group": "Copy to clipboard",
                        "caption": "Quicktime path",
                        "description": "Copy the quicktime path associated with this version to the clipboard.",
                    }
                )

        if "sequence_clipboard" in actions:

            if sg_data.get("sg_path_to_frames"):
                # path to frames exists, so show the action
                action_instances.append(
                    {
                        "name": "sequence_clipboard",
                        "params": None,
                        "group": "Copy to clipboard",
                        "caption": "Image sequence path",
                        "description": "Copy the image sequence path associated with this version to the clipboard.",
                    }
                )

        if "publish_clipboard" in actions:

            if "path" in sg_data and sg_data["path"].get("local_path"):
                # path field exists and the local path is populated
                action_instances.append(
                    {
                        "name": "publish_clipboard",
                        "params": None,
                        "group": "Copy to clipboard",
                        "caption": "Path on disk",
                        "description": "Copy the path associated with this publish to the clipboard.",
                    }
                )

        if "add_to_playlist" in actions and ui_area == "details":
            # retrieve the 10 most recently updated non-closed playlists for this project

            from tank_vendor.shotgun_api3.lib.sgtimezone import LocalTimezone

            datetime_now = datetime.datetime.now(LocalTimezone())

            playlists = self.parent.shotgun.find(
                "Playlist",
                [
                    ["project", "is", sg_data.get("project")],
                    {
                        "filter_operator": "any",
                        "filters": [
                            ["sg_date_and_time", "greater_than", datetime_now],
                            ["sg_date_and_time", "is", None],
                        ],
                    },
                ],
                ["code", "id", "sg_date_and_time"],
                order=[{"field_name": "updated_at", "direction": "desc"}],
                limit=10,
            )

            # playlists this version is already part of
            existing_playlist_ids = [x["id"] for x in sg_data.get("playlists", [])]

            for playlist in playlists:
                if playlist["id"] in existing_playlist_ids:
                    # version already in this playlist so skip
                    continue

                if playlist.get("sg_date_and_time"):
                    # playlist name includes date/time
                    caption = "%s (%s)" % (
                        playlist["code"],
                        self._format_timestamp(playlist["sg_date_and_time"]),
                    )
                else:
                    caption = playlist["code"]

                self.logger.debug(
                    "Created add to playlist action for playlist %s" % playlist
                )

                action_instances.append(
                    {
                        "name": "add_to_playlist",
                        "group": "Add to playlist",
                        "params": {"playlist_id": playlist["id"]},
                        "caption": caption,
                        "description": "Add the version to this playlist.",
                    }
                )

        # TODO - We will need to define a bit more the different action
        # We also bypass the actions check from the yml since we know we want to launch dcc app
        # We should only allow this possibility when in tk-desktop engine only
        if self.parent.engine.name == 'tk-desktop':
            if sg_data.get("type", None) == 'Task':
                all_actions = self.get_actions(sg_data["type"], sg_data["id"])
                action_instances.extend(all_actions)
                '''
                action_instances.append(
                    {"name": "start_dcc",
                     "params": None,
                     "caption": "Start Application",
                     "description": "Start the software associated to the task"})
                '''

        return action_instances

    def get_actions(self, entity_type, entity_id):
        """
        Get the rez env information + the shotgun yml env information to compare them and give the
        current possible actions

        :return: List of possible actions given to the user
        """

        action_list = []

        ctx = self.parent.engine.tank.context_from_entity(entity_type, entity_id)
        launchapp = self.parent.engine.apps['tk-multi-launchapp']
        # Get all the rez package accessible for the current environment
        rez_pkg = launchapp.execute_hook("hook_get_rez_packages", context=ctx)
        # Gather the current context yml information
        env, descriptor = sgtk.platform.engine.get_env_and_descriptor_for_engine('tk-shotgun', self.parent.sgtk, ctx)

        all_apps = env.get_apps('tk-shotgun')
        for app_name in all_apps:
            settings = env.get_app_settings('tk-shotgun', app_name)
            app_engine = settings.get('engine', None)
            if app_engine:
                base_engine_name = app_engine.replace('tk-', '')
                # Rez package is named photoshop and not photoshopcc
                if base_engine_name == 'photoshopcc':
                    base_engine_name = 'photoshop'
                engine_regex = base_engine_name + '.*'
                for pkg in rez_pkg:
                    if re.match(engine_regex, pkg, re.IGNORECASE):
                        app_menu_name = settings.get('menu_name', None)
                        # Taken from tk-multi-launchapp/base_launcher.py/_register_launch_command
                        command_name = app_menu_name.lower().replace(" ", "_")
                        if command_name.endswith("..."):
                            command_name = command_name[:-3]
                        action_list.append({"name": command_name,
                                            "params": None,
                                            "caption": app_menu_name,
                                            "description": "Launch {} for the selected task".format(base_engine_name)})
                        break

        return action_list

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: Shotgun data dictionary
        :returns: Dictionary representing an Entity if action requires a context change in the panel,
                  otherwise no return value expected.
        """
        app = self.parent
        app.log_debug(
            "Execute action called for action %s. "
            "Parameters: %s. SG Data: %s" % (name, params, sg_data)
        )

        if name == "assign_task":
            if app.context.user is None:
                raise Exception(
                    "SG Toolkit does not know what SG user you are. "
                    "This can be due to the use of a script key for authentication "
                    "rather than using a user name and password login. To assign a "
                    "Task, you will need to log in using you SG user account."
                )

            data = app.shotgun.find_one(
                "Task", [["id", "is", sg_data["id"]]], ["task_assignees"]
            )
            assignees = data["task_assignees"] or []
            assignees.append(app.context.user)
            app.shotgun.update("Task", sg_data["id"], {"task_assignees": assignees})

        elif name == "add_to_playlist":
            app.shotgun.update(
                "Version",
                sg_data["id"],
                {"playlists": [{"type": "Playlist", "id": params["playlist_id"]}]},
                multi_entity_update_modes={"playlists": "add"},
            )
            self.logger.debug(
                "Updated playlist %s to include version %s"
                % (params["playlist_id"], sg_data["id"])
            )

        elif name == "task_to_ip":
            app.shotgun.update("Task", sg_data["id"], {"sg_status_list": "ip"})

        elif name == "quicktime_clipboard":
            self._copy_to_clipboard(sg_data["sg_path_to_movie"])

        elif name == "sequence_clipboard":
            self._copy_to_clipboard(sg_data["sg_path_to_frames"])

        elif name == "publish_clipboard":
            self._copy_to_clipboard(sg_data["path"]["local_path"])

        elif re.match("launch_.*", name):
            self._start_application(sg_data["type"], sg_data["id"], name)

        return dict()

    def execute_entity_doubleclicked_action(self, sg_data):
        """
        This action is triggered when an entity is double-clicked.
        Return True to indicate to the caller to continue with the
        double-click action, or False to abort the action.

        This base hook method simply returns True to continue with the
        double-click action without any custom actions. Override this
        method to perform any specific handling.

        :param sg_data: Dictionary containing data for the entity that
                        was double-clicked.
        :return: True if the panel should navigate to the entity that was
                 double-clicked, else False.
        :rtype: bool
        """

        return True

    def _copy_to_clipboard(self, text):
        """
        Helper method - copies the given text to the clipboard

        :param text: content to copy
        """
        from sgtk.platform.qt import QtCore, QtGui

        QtGui.QApplication.clipboard().setText(text)

    def _format_timestamp(self, datetime_obj):
        """
        Formats the given datetime object in a short human readable form.

        :param datetime_obj: Datetime obj to format
        :returns: date str
        """
        from tank_vendor.shotgun_api3.lib.sgtimezone import LocalTimezone

        datetime_now = datetime.datetime.now(LocalTimezone())

        datetime_tomorrow = datetime_now + datetime.timedelta(hours=24)

        if datetime_obj.date() == datetime_now.date():
            # today - display timestamp - Today 01:37AM
            return datetime_obj.strftime("Today %I:%M%p")

        elif datetime_obj.date() == datetime_tomorrow.date():
            # tomorrow - display timestamp - Tomorrow 01:37AM
            return datetime_obj.strftime("Tomorrow %I:%M%p")

        else:
            # 24 June 01:37AM
            return datetime_obj.strftime("%d %b %I:%M%p")

    def _start_application(self, entity_type, entity_id, command_name):
        """
        Helper method to start the good dcc application

        :param entity_type: The type of entity we want to look at
        :param entity_id: The id of the entity
        """

        def _compute_sys_path():
            """
            Taken from tk-framework-desktopserver - api_v2.py - _compute_sys_path

            :returns: Path to the current core.
            """
            # While core swapping, the Python path is not updated with the new core's Python path,
            # so make sure the current core is at the front of the Python path for out subprocesses.
            python_folder = sgtk.bootstrap.ToolkitManager.get_core_python_path()
            return [python_folder] + sys.path

        def _get_arguments_file(args_data):
            """
            Taken from tk-framework-desktopserver - api_v2.py - _get_arguments_file

            Dumps out a temporary file containing the provided data structure.

            :param args_data: The data to serialize to disk.

            :returns: File path
            :rtype: str
            """
            args_file = tempfile.mkstemp()[1]

            with open(args_file, "wb") as fh:
                cPickle.dump(
                    args_data,
                    fh,
                    cPickle.HIGHEST_PROTOCOL,
                )

            return args_file

        def _get_python_interpreter(descriptor):
            """
            Taken from tk-framework-desktopserver - api_v2.py - _get_python_interpreter

            Retrieves the python interpreter from the configuration. Returns the
            current python interpreter if no interpreter was specified.
            """
            try:
                path_to_python = descriptor.python_interpreter
            except:
                if sys.platform == "darwin":
                    path_to_python = os.path.join(sys.prefix, "bin", "python")
                elif sys.platform == "win32":
                    path_to_python = os.path.join(sys.prefix, "python.exe")
                else:
                    path_to_python = os.path.join(sys.prefix, "bin", "python")
            return path_to_python

        def _get_toolkit_manager(base_config_uri):
            """
            Taken from tk-framework-desktopserver - api_v2.py - _get_toolkit_manager

            Gets an initialized ToolkitManager object.

            :returns: A ToolkitManager object.
            """
            TOOLKIT_MANAGER = sgtk.bootstrap.ToolkitManager()
            TOOLKIT_MANAGER.allow_config_overrides = False
            TOOLKIT_MANAGER.plugin_id = "basic.shotgun"
            TOOLKIT_MANAGER.base_configuration = base_config_uri

            return TOOLKIT_MANAGER

        # Import the module to make sure it's correctly imported
        desktopserver_module = sgtk.platform.current_engine().frameworks[
            'tk-framework-desktopserver'].import_module(
            'tk_framework_desktopserver')

        sg = sgtk.api.shotgun.get_sg_connection()

        entity = sg.find_one(entity_type, [["id", "is", entity_id]], ["project"])
        project_entity = entity['project']
        entities = [entity]

        if self.parent.tank.pipeline_configuration.is_unmanaged():
            config_entity = sg.find_one('PipelineConfiguration', [["project", "is", project_entity],
                                                                  ["code", "is", "Primary"]])
        else:
            config_entity = sg.find_one('PipelineConfiguration', [["project", "is", project_entity],
                                                                  ["id", "is",
                                                                   self.parent.tank.pipeline_configuration.get_shotgun_id()]])
        # config_descriptor = config_entity.pop('descriptor', None)

        # Most of the code bellow have been taken from tk-framework-desktopserver - api_v2.py - _execute_action

        args_file = _get_arguments_file(
            dict(
                config=config_entity,
                name=command_name,
                entities=entities,
                project=project_entity,
                sys_path=_compute_sys_path(),
                base_configuration=desktopserver_module.shotgun.constants.BASE_CONFIG_URI,
                engine_name=desktopserver_module.shotgun.constants.ENGINE_NAME,
                logging_prefix=desktopserver_module.shotgun.constants.LOGGING_PREFIX,
                bundle_cache_fallback_paths=[]
            ),
        )

        module_path = desktopserver_module.shotgun.__path__[0]

        script = os.path.join(
            module_path,
            "scripts",
            "execute_command.py"
        )

        # We'll need the Python executable when we shell out. We need to make
        # sure it's what's in the config's interpreter config file. To do that,
        # we can get the config's descriptor object from the manager and ask
        # it for the path. By this point, all of the config data has been cached,
        # because it will have been looked up as part of the get_actions method
        # when the menu asked for actions, so getting the manager and all of the
        # config data will be essentially free.

        # manager = _get_toolkit_manager(desktopserver_module.shotgun.constants.BASE_CONFIG_URI)
        # manager.bundle_cache_fallback_paths = self._engine.sgtk.bundle_cache_fallback_paths
        '''
        all_pc_data = self._get_pipeline_configuration_data(
            manager,
            project_entity,
            data,
            )
        '''

        # At the moment, we will give a bad descriptor and always take the python interpreter found on the machine
        python_exe = _get_python_interpreter('')

        args = [python_exe, script, args_file]

        # Ensure the credentials are still valid before launching the command in
        # a separate process. We need do to this in advance because the process
        # that will be launched might not have PySide and as such won't be able
        # to prompt the user to re-authenticate.

        # If you are running in Shotgun Desktop 1.0.2 there is no authenticated
        # user, only a script user, so skip this.
        if sgtk.get_authenticated_user():
            sgtk.get_authenticated_user().refresh_credentials()

        Command.call_cmd(args)


class Command(object):
    """
    Class taken from tk-framework-desktopserver command.py.
    It have been modified to not wait for the started process and not block the shotgunpanel
    """

    @staticmethod
    def _create_temp_file():
        """
        :returns: Returns the path to a temporary file.
        """
        handle, path = tempfile.mkstemp(prefix="desktop_server")
        os.close(handle)
        return path

    @staticmethod
    def call_cmd(args):
        """
        Runs a command in a separate process.

        :param args: Command line tokens.
        """
        # The commands that are being run are probably being launched from Desktop, which would
        # have a TANK_CURRENT_PC environment variable set to the site configuration. Since we
        # preserve that value for subprocesses (which is usually the behavior we want), the DCCs
        # being launched would try to run in the project environment and would get an error due
        # to the conflict.
        #
        # Clean up the environment to prevent that from happening.
        env = os.environ.copy()
        vars_to_remove = ["TANK_CURRENT_PC"]
        for var in vars_to_remove:
            if var in env:
                del env[var]

        # Launch the child process
        # Due to discrepencies on how child file descriptors and shell=True are
        # handled on Windows and Unix, we'll provide two implementations. See the Windows
        # implementation for more details.
        if sys.platform == "win32":
            Command._call_cmd_win32(args, env)
        else:
            Command._call_cmd_unix(args, env)

    @staticmethod
    def _call_cmd_unix(args, env):
        """
        Runs a command in a separate process. Implementation for Unix based OSes.

        :param args: Command line tokens.
        :param env: Environment variables to set for the subprocess.
        """
        try:
            process = subprocess.Popen(
                args,
                stdin=None, stdout=None, stderr=None, env=env
            )
            # Popen.communicate() doesn't play nicely if the stdin pipe is closed
            # as it tries to flush it causing an 'I/O error on closed file' error
            # when run from a terminal
            #
            # to avoid this, lets just poll the output from the process until
            # it's finished
            # process.wait()
        except Exception:
            print("Cannot start process with args {}".format(args))

    @staticmethod
    def _call_cmd_win32(args, env):
        """
        Runs a command in a separate process. Implementation for Windows.

        :param args: Command line tokens.
        :param env: Environment variables to set for the subprocess.

        :returns: A tuple containing (exit code, stdout, stderr).
        """
        stdout_lines = []
        stderr_lines = []
        try:
            stdout_path = Command._create_temp_file()
            stderr_path = Command._create_temp_file()

            # On Windows, file descriptors like sockets can be inherited by child
            # process and are only closed when the main process and all child
            # processes are closed. This is bad because it means that the port
            # the websocket server uses will never be released as long as any DCCs
            # or tank commands are running. Therefore, closing the Desktop and
            # restarting it for example wouldn't free the port and would give the
            # "port 9000 already in use" error we've seen before.

            # To avoid this, close_fds needs to be specified when launching a child
            # process. However, there's a catch. On Windows, specifying close_fds
            # also means that you can't share stdout, stdin and stderr with the child
            # process, which is required here because we want to capture the output
            # of the process.

            # Therefore on Windows we'll invoke the code in a shell environment. The
            # output will be redirected to two temporary files which will be read
            # when the child process is over.

            # Ideally, we'd be using this implementation on Unix as well. After all,
            # the syntax of the command line is the same. However, specifying shell=True
            # on Unix means that the following ["ls", "-al"] would be invoked like this:
            # ["/bin/sh", "-c", "ls", "-al"]. This means that only ls is sent to the
            # shell and -al is considered to be an argument of the shell and not part
            # of what needs to be launched. The naive solution would be to quote the
            # argument list and pass ["\"ls -al \""] to Popen, but that would ignore
            # the fact that there could already be quotes on that command line and
            # they would need to be escaped as well. Python 2's only utility to
            # escape strings for the command line is pipes.quote, which is deprecated.

            # Because of these reasons, we'll keep both implementations for now.

            args = args + ["1>", stdout_path, "2>", stderr_path]

            # Prevents the cmd.exe dialog from appearing on Windows.
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                args,
                close_fds=True,
                startupinfo=startupinfo,
                env=env,
                shell=True
            )

        except Exception:
            print("Cannot start process with args {}".format(args))

        # Don't lose any sleep over temporary files that can't be deleted.
        try:
            os.remove(stdout_path)
        except:
            pass
        try:
            os.remove(stderr_path)
        except:
            pass
