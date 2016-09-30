#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Test cases of perforce to svn replication
'''


import os
import unittest
import tempfile

from testcommon import get_p4d_from_docker
from testcommon_p4svn import replicate_P4SvnReplicate, verify_replication
from lib.buildlogger import getLogger
from lib.buildcommon import generate_random_str
import testp4svn_samples

logger = getLogger(__name__)


class P4SvnActionRepTest(testp4svn_samples.P4SvnReplicationTest):

    def p4svn_action_remove_setup_env(self, depot_dir, action, **kwargs):
        levels_of_dir = kwargs.get('levels_of_dir', 0)
        place_holder_file = kwargs.get('place_holder_file', -1)

        src_docker_cli = self.docker_p4d_clients['p4d_0']
        with get_p4d_from_docker(src_docker_cli, depot_dir) as p4:
            clientspec = p4.fetch_client(p4.client)
            ws_root = clientspec._root

            project_dir =  'a_dir'
            project_dir = tempfile.mkdtemp(prefix=project_dir, dir=ws_root)

            # add a file in project dir
            proj_file_path = os.path.join(project_dir, 'project_file')
            description = 'add a file with file name %s' % proj_file_path
            with open(proj_file_path, 'wt') as f:
                f.write('My name is %s!\n' % proj_file_path)
            p4.run_add('-f', proj_file_path)
            p4.run_submit('-d', description)

            # make a directory and add files in it
            file_names = ['a_file.txt', 'another_file.txt',
                          'yet_another_file.txt']

            test_dir = tempfile.mkdtemp(dir=project_dir)
            for i in range(levels_of_dir):
                test_dir = tempfile.mkdtemp(dir=test_dir, prefix='%s_' % i)
                if place_holder_file == i:
                    file_path = os.path.join(test_dir, 'place_holder')
                    with open(file_path, 'wt') as f:
                        f.write('prevent deletion of dir!\n')
                    p4.run_add('-f', file_path)
                    p4.run_submit('-d', 'add a file to prevent deletion of dir')

            # add the files
            for fn in file_names:
                file_path = os.path.join(test_dir, fn)
                description = 'add a file with file name %s' % fn
                with open(file_path, 'wt') as f:
                    f.write('My name is %s!\n' % fn)
                p4.run_add('-f', file_path)
                p4.run_submit('-d', description)

            if action == 'remove_one_by_one':
                # remove all files one by one
                for fn in file_names:
                    file_path = os.path.join(test_dir, fn)
                    description = 'remove %s' % fn
                    p4.run_delete(file_path)
                    p4.run_submit('-d', description)
            elif action == 'remove_all_in_one_change':
                # remove all files all together
                description = ''
                for fn in file_names:
                    file_path = os.path.join(test_dir, fn)
                    description += 'remove %s\n' % fn
                    p4.run_delete(file_path)
                p4.run_submit('-d', description)
            elif action in ['remove_all_add_one',
                            'remove_all_add_one_in_parent']:
                # 1) remove_all_add_one
                # remove all files all together but add a new file in
                # the same directory, no directory should be deleted
                # 2) remove_all_add_on_in_parent
                # remove all files all together and add a new file in
                # the parent directory, current directory should be deleted
                description = ''
                for fn in file_names:
                    file_path = os.path.join(test_dir, fn)
                    description += 'remove %s\n' % fn
                    p4.run_delete(file_path)

                file_path = os.path.join(test_dir, 'fantastic_additional')
                if action == 'remove_all_add_one_in_parent':
                    test_dir_parent = os.path.split(test_dir)[0]
                    file_path = os.path.join(test_dir_parent, 'fantastic_additional')
                description = 'add a file with file name %s' % fn
                with open(file_path, 'wt') as f:
                    f.write('My name is %s!\n' % fn)
                p4.run_add('-f', file_path)
                p4.run_submit('-d', description)
            else:
                logger.error('"%s" not yet implemented' % action)

            p4.run_edit(proj_file_path)
            with open(proj_file_path, 'a') as f:
                f.write('My name is %s!\n' % proj_file_path)
            p4.run_submit('-d', 'editing %s' % proj_file_path)

    def test_p4svn_action_remove_empty_dir_one_by_one(self):
        '''test that directory should be removed automatically if all files in
        it are removed one by one.
        '''
        test_case = 'p4svn_action_remove_empty_dir_one_by_one'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir, action='remove_one_by_one')

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_all_files_in_one_change(self):
        '''test that directory should be removed automatically if all files in
        it are removed in one change.
        '''
        test_case = 'p4svn_action_remove_empty_dir_all_files_in_one_change'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_all_in_one_change')

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_all_files_in_one_change_multi_levels(self):
        '''test that directories should be removed recursivly if files in
        them are removed.
        '''
        test_case = 'p4svn_action_remove_empty_dir_all_files_in_one_change_multi_levels'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_all_in_one_change',
                                           levels_of_dir=2)

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_one_by_one_multi_levels(self):
        '''test that directories should be removed recursivly if files in
        them are removed.
        '''
        test_case = 'p4svn_action_remove_empty_dir_one_by_one_multi_levels'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_one_by_one',
                                           levels_of_dir=2)

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_one_by_one_multi_levels_place_holder(self):
        '''test that directory should not be removed automatically if some
        file in it is still there.
        '''
        test_case = 'p4svn_action_remove_empty_dir_one_by_one_multi_levels_place_holder'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_one_by_one',
                                           levels_of_dir=4,
                                           place_holder_file=1)

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_remove_all_add_one(self):
        '''test that directory should not be removed automatically if new
        file is added to it.
        '''
        test_case = 'p4svn_action_remove_empty_dir_remove_all_add_one'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_all_add_one',
                                           levels_of_dir=4)

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)

    def test_p4svn_action_remove_empty_dir_remove_all_add_one_in_parent(self):
        '''test that directory should not be removed automatically if new
        file is added to it.
        '''
        test_case = 'p4svn_action_remove_empty_dir_remove_all_add_one_in_parent'
        depot_dir = '/depot/%s' % test_case
        src_docker_cli = self.docker_p4d_clients['p4d_0']
        dst_docker_cli = self.docker_svn_clients['svn_0']

        self.p4svn_action_remove_setup_env(depot_dir,
                                           action='remove_all_add_one_in_parent',
                                           levels_of_dir=4)

        self.replicate_sample_dir_withdocker(depot_dir)
        logger.passed(test_case)



    def test_p4_action_rep_special_commitmsgs(self):
        commitmsgs = {'utf-8':u'I think, therefore I am.',
                      'cp1251':u'мыслю, следовательно существую.',
                      'gb2312':u'我思故我在.',
                      'latin1':u'La Santé',}

        pass


if __name__ == '__main__':
    unittest.main()
