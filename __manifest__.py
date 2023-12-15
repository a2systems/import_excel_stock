{
    "name": "import_excel_stock",
    "summary": """
        Importacion de stocks
        """,
    "description": """
    """,
    "category": "Stock",
    "version": "1.0",
    # any module necessary for this one to work correctly
    "depends": ["base","stock"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/stock_file.xml"
    ],
    'license': 'LGPL-3',
}
