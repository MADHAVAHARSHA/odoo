{
    "name": "Icashout payment integration",
    "author": "Icashout Systems",
    "license": "LGPL-3",
    'category': 'Sales/Point of Sale',
    "version": "18.0.1.0",
    'depends': ['payment','point_of_sale','web'],

    'post_init_hook': 'create_manual_entry_method_if_missing',
    'uninstall_hook': 'uninstall_remove_manual_entry',

    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/manualentrycreation.xml',

    ],

'assets': {
        'point_of_sale._assets_pos': [
            'Datacap/static/src/js/payment_datacap.js',
            'Datacap/static/src/js/model.js',
            'Datacap/static/src/js/pos_payment_extension.js',
            'Datacap/static/src/xml/refundvoid.xml',
            'Datacap/static/src/js/payment_split.js',
            'Datacap/static/src/xml/payment_split.xml',
            # 'Datacap/static/src/xml/payment_method_add.xml',
            'Datacap/static/src/js/ticketextend.js',
            'Datacap/static/src/xml/void.xml',
            'Datacap/static/src/js/void.js',
            'Datacap/static/src/xml/receipt_extension.xml',
            # 'Datacap/static/src/js/setNumberBuffer.js',
            # 'Datacap/static/src/xml/Batch_summary_close.xml',
            # 'Datacap/static/src/js/navbar_batch_button.js',
        ],
},
    'installable': True,
    'application': False,
}


