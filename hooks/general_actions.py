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
                
        :param sg_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        '''
        paths = (
            '/opt/squeeze/PyCharm/helpers/pydev',
            '/opt/squeeze/PyCharm-2016.2.3/helpers/pydev',
            '/opt/squeeze/PyCharm-2016.3.2/helpers/pydev',
            '/opt/squeeze/PyCharm-2017.1.1/helpers/pydev',
            'C:/Program Files (x86)/JetBrains/PyCharm 2016.2.3/helpers/pydev',
            'C:/Program Files/JetBrains/PyCharm 2017.1.1/helpers/pydev',
            'C:/Program Files/JetBrains/PyCharm 2017.1.4/helpers/pydev',
            '/opt/pycharm-professional/helpers/pydev/'  # arch-linux
        )
        path = next(iter(path for path in paths if os.path.exists(path)), None)
        if not path or not os.path.exists(path):
            raise Exception("Can't connect to pycharm, path doesn't exist: {0}".format(path))
        if path not in sys.path:
            sys.path.append(path)
        import pydevd
        pydevd.settrace('localhost', port=64304, stdoutToServer=True, stderrToServer=True, suspend=False)
        '''

        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Shotgun Data: %s" % (ui_area, actions, sg_data))
        
        action_instances = []
        
        if "assign_task" in actions:
            action_instances.append( 
                {"name": "assign_task", 
                  "params": None,
                  "caption": "Assign Task to yourself", 
                  "description": "Assign this task to yourself."} )

        if "task_to_ip" in actions:
            action_instances.append( 
                {"name": "task_to_ip", 
                  "params": None,
                  "caption": "Set to In Progress", 
                  "description": "Set the task status to In Progress."} )

        if "quicktime_clipboard" in actions:
            
            if sg_data.get("sg_path_to_movie"):
                # path to movie exists, so show the action
                action_instances.append( 
                    {"name": "quicktime_clipboard", 
                      "params": None,
                      "caption": "Copy quicktime path to clipboard", 
                      "description": "Copy the quicktime path associated with this version to the clipboard."} )

        if "sequence_clipboard" in actions:

            if sg_data.get("sg_path_to_frames"):
                # path to frames exists, so show the action            
                action_instances.append( 
                    {"name": "sequence_clipboard", 
                      "params": None,
                      "caption": "Copy image sequence path to clipboard", 
                      "description": "Copy the image sequence path associated with this version to the clipboard."} )

        if "publish_clipboard" in actions:
            
            if "path" in sg_data and sg_data["path"].get("local_path"): 
                # path field exists and the local path is populated
                action_instances.append( 
                    {"name": "publish_clipboard", 
                      "params": None,
                      "caption": "Copy path to clipboard", 
                      "description": "Copy the path associated with this publish to the clipboard."} )


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
        :returns: No return value expected.
        """
        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Shotgun Data: %s" % (name, params, sg_data))
        
        if name == "assign_task":
            if app.context.user is None:
                raise Exception("Cannot establish current user!")
            
            data = app.shotgun.find_one("Task", [["id", "is", sg_data["id"]]], ["task_assignees"] )
            assignees = data["task_assignees"] or []
            assignees.append(app.context.user)
            app.shotgun.update("Task", sg_data["id"], {"task_assignees": assignees})

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
            
        
    def _copy_to_clipboard(self, text):
        """
        Helper method - copies the given text to the clipboard
        
        :param text: content to copy
        """
        from sgtk.platform.qt import QtCore, QtGui
        app = QtCore.QCoreApplication.instance()
        app.clipboard().setText(text)

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
        desktopserver_module = sgtk.platform.current_engine().frameworks['tk-framework-desktopserver'].import_module(
            'tk_framework_desktopserver')

        sg = sgtk.api.shotgun.get_sg_connection()

        entity = sg.find_one(entity_type, [["id", "is", entity_id]], ["project"])
        project_entity = entity['project']
        entities = [entity]
        config_entity = sg.find_one('PipelineConfiguration', [["project", "is", project_entity],
                                                              ["code", "is", "Primary"]], ["id", "code", "descriptor"])
        config_descriptor = config_entity.pop('descriptor', None)

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

        '''
        import sgtk

        mgr = sgtk.bootstrap.ToolkitManager()
        mgr.base_configuration = r'sgtk:descriptor:dev?path=C:\Users\Sbourgoing\Documents\dev\tk_config_moov\config'
        mgr.allow_config_overrides = False
        mgr.plugin_id = "basic.shotgun"

        # Re-import sgtk to get the good core
        import sgtk

        e = mgr.bootstrap_engine("tk-shotgun", entity={"type": entity_type, "id": entity_id})

        e.tank.create_filesystem_structure(entity_type, entity_id)

        cmd_callback = e.commands['launch_maya']["callback"]
        cmd_callback()
        #e._has_qt = False
        #e.execute_old_style_command("launch_maya", entity_type, [entity_id])
        # e.execute_command("launch_maya")

        # e.apps['tk-shotgun-launchmaya'].launch_from_path_and_context('', context=e.context)

        print "Here you go !"
        

        
        ctx = sgtk.platform.current_engine().apps['tk-shotgun-launchmaya'].tank.context_from_entity(entity_type,
                                                                                                    entity_id)
        # Update path_cache.db for the site configuration
        sgtk.platform.current_engine().tank.create_filesystem_structure(entity_type, entity_id)
        # TODO - setup the good path from the os using the settings in the app
        sgtk.platform.current_engine().apps['tk-shotgun-launchmaya'].launch_from_path_and_context('maya', context=ctx)
        # sgtk.platform.current_engine().apps['tk-shotgun-launchmaya'].settings
        '''


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
        except StandardError:
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

        except StandardError:
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