from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'langrobot'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'worlds'), glob('../../worlds/*.sdf')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config', 'rviz'), glob('config/rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Benas Vaiciulis',
    maintainer_email='benas@example.com',
    description='Language-driven robot manipulation system',
    license='MIT',
    entry_points={
        'console_scripts': [
            'controller_node = langrobot.controller_node:main',
        ],
    },
)
