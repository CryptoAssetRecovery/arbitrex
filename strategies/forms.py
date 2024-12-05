# strategies/forms.py

from django import forms
from .models import Strategy
import backtrader as bt

import pkg_resources

STRATEGY_TEMPLATE = '''
import backtrader as bt

class CustomStrategy(bt.Strategy):
    params = (
        ('param_name', default_value),
    )

    def __init__(self):
        # Initialize indicators
        pass

    def next(self):
        # Define your trading logic
        pass
'''

class StrategyForm(forms.ModelForm):
    class Meta:
        model = Strategy
        fields = ['name', 'description', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900',
                'placeholder': 'Enter strategy name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900',
                'rows': 3,
                'placeholder': 'Describe your strategy'
            }),
            'code': forms.Textarea(attrs={
                'class': 'w-full font-mono bg-white text-gray-900',
                'rows': 10,
                'placeholder': 'Enter your strategy code'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(StrategyForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            # Autofill with template if creating a new Strategy
            self.fields['code'].initial = STRATEGY_TEMPLATE

    def clean_code(self):
        code = self.cleaned_data.get('code')

        installed_packages = {pkg.key for pkg in pkg_resources.working_set}
        
        # Step 1: Syntax checking using compile()
        try:
            compiled_code = compile(code, '<string>', 'exec')
        except SyntaxError as e:
            raise forms.ValidationError(f"Syntax error in code: {e}")

        # Step 2: Analyzing the AST
        import ast
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise forms.ValidationError(f"Syntax error in code: {e}")

        # Look for a class that inherits from bt.Strategy
        strategy_class_found = False
        strategy_methods = set()
        required_methods = {'next'}

        class StrategyVisitor(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                nonlocal strategy_class_found
                # Check base classes
                for base in node.bases:
                    base_name = self.get_base_name(base)
                    if base_name in ('bt.Strategy', 'Strategy'):
                        strategy_class_found = True
                        # Collect method names
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                strategy_methods.add(item.name)
                self.generic_visit(node)

            def get_base_name(self, base):
                if isinstance(base, ast.Attribute):
                    return f"{self.get_base_name(base.value)}.{base.attr}"
                elif isinstance(base, ast.Name):
                    return base.id
                else:
                    return ''

            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name in ['os', 'sys', 'subprocess']:
                        raise forms.ValidationError(f"Importing '{alias.name}' is not allowed.")
                    
                    # Check if package is installed
                    package_name = alias.name.split('.')[0]  # Get base package name
                    if package_name not in installed_packages and package_name not in ['backtrader', 'bt']:
                        raise forms.ValidationError(f"Package '{package_name}' is not installed.")
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module in ['os', 'sys', 'subprocess']:
                    raise forms.ValidationError(f"Importing from '{node.module}' is not allowed.")
                    
                # Check if package is installed
                package_name = node.module.split('.')[0]  # Get base package name
                if package_name not in installed_packages and package_name not in ['backtrader', 'bt']:
                    raise forms.ValidationError(f"Package '{package_name}' is not installed. Please add it to requirements.txt")
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec', 'open']:
                        raise forms.ValidationError(f"Using '{node.func.id}' is not allowed.")
                self.generic_visit(node)

        visitor = StrategyVisitor()
        visitor.visit(tree)

        if not strategy_class_found:
            raise forms.ValidationError("The code must define a class that inherits from bt.Strategy.")

        missing_methods = required_methods - strategy_methods
        if missing_methods:
            raise forms.ValidationError(f"The Strategy class is missing required methods: {', '.join(missing_methods)}")

        return code