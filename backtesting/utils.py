import ast

def update_strategy_params_in_code(code, new_params):
    tree = ast.parse(code)
    for node in tree.body:
        # Identify classes that inherit from something that eventually is 'Strategy'
        if isinstance(node, ast.ClassDef):
            # Check bases for something named 'Strategy', even if it's bt.Strategy
            is_strategy = any(
                (isinstance(base, ast.Name) and base.id == 'Strategy') or
                (isinstance(base, ast.Attribute) and base.attr == 'Strategy')
                for base in node.bases
            )
            if is_strategy:
                # Found a Strategy class, now find 'params' assignment
                for attr in node.body:
                    if isinstance(attr, ast.Assign) and len(attr.targets) == 1:
                        target = attr.targets[0]
                        if isinstance(target, ast.Name) and target.id == 'params':
                            # Build a new tuple node from the new_params dict
                            items = []
                            for k, v in new_params.items():
                                # Convert strings to appropriate types if needed
                                # If you know some params should be integers, convert them:
                                # Example: if v can be converted to int or float
                                try:
                                    v = int(v)
                                except ValueError:
                                    try:
                                        v = float(v)
                                    except ValueError:
                                        pass
                                items.append(ast.Tuple(
                                    elts=[ast.Constant(k), ast.Constant(v)],
                                    ctx=ast.Load()
                                ))
                            attr.value = ast.Tuple(elts=items, ctx=ast.Load())

    updated_code = ast.unparse(tree)
    return updated_code
