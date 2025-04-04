"""
News AI Package - AI-powered newsletter system
"""

__version__ = '1.0.0'
__author__ = 'HomeSmartify'

# Make key modules available at package level
try:
    from . import subscriber_mgt
    from . import Newsletter_page
except ImportError:
    # Handle case where modules are imported directly
    pass 