from setuptools import setup

setup(name='PlanetLab measurement',
      version='1.0',
      description='OpenShift App',
      author='Rudolf Horvath',
      author_email='rudolf.official@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',
      install_requires=[
        # 'Django>=1.3',
        'flask>=0.10',
        'paramiko>=1.15.2',
        'simplejson>=3.8',
        'requests>=2.7',
        # 'requests[security]',
        'dnspython>=1.12',
        'pymongo>=3.0.3',
        'pycrypto>=2.6.1',
        'ecdsa>=0.13'
      ],
      )


