#!/usr/bin/env python3
"""
Test script for the verification functionality
"""

import unittest
from unittest.mock import MagicMock, patch
from utils import verify_table_population

class TestVerification(unittest.TestCase):
    """Test cases for the verification functionality"""

    def test_all_tables_populated(self):
        """Test when all tables are properly populated"""
        # Mock database connector
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = lambda query: [{'count': 10}]
        
        # Test tables
        tables = ['table1', 'table2', 'table3']
        
        # Run verification
        success, empty_tables, partially_populated_tables = verify_table_population(
            mock_db, tables, min_records=5
        )
        
        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(empty_tables), 0)
        self.assertEqual(len(partially_populated_tables), 0)
        
        # Verify that execute_query was called for each table
        self.assertEqual(mock_db.execute_query.call_count, 3)
    
    def test_empty_tables(self):
        """Test when some tables are empty"""
        # Mock database connector
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [{'count': 10}],  # table1
            [{'count': 0}],   # table2
            [{'count': 5}]    # table3
        ]
        
        # Test tables
        tables = ['table1', 'table2', 'table3']
        
        # Run verification
        success, empty_tables, partially_populated_tables = verify_table_population(
            mock_db, tables, min_records=5
        )
        
        # Assertions
        self.assertFalse(success)
        self.assertEqual(len(empty_tables), 1)
        self.assertEqual(empty_tables[0], 'table2')
        self.assertEqual(len(partially_populated_tables), 0)
    
    def test_partially_populated_tables(self):
        """Test when some tables are partially populated"""
        # Mock database connector
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [{'count': 10}],  # table1
            [{'count': 3}],   # table2
            [{'count': 5}]    # table3
        ]
        
        # Test tables
        tables = ['table1', 'table2', 'table3']
        
        # Run verification
        success, empty_tables, partially_populated_tables = verify_table_population(
            mock_db, tables, min_records=5
        )
        
        # Assertions
        self.assertFalse(success)
        self.assertEqual(len(empty_tables), 0)
        self.assertEqual(len(partially_populated_tables), 1)
        self.assertEqual(partially_populated_tables['table2'], 3)
    
    def test_mixed_issues(self):
        """Test when there are both empty and partially populated tables"""
        # Mock database connector
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [{'count': 10}],  # table1
            [{'count': 0}],   # table2
            [{'count': 3}]    # table3
        ]
        
        # Test tables
        tables = ['table1', 'table2', 'table3']
        
        # Run verification
        success, empty_tables, partially_populated_tables = verify_table_population(
            mock_db, tables, min_records=5
        )
        
        # Assertions
        self.assertFalse(success)
        self.assertEqual(len(empty_tables), 1)
        self.assertEqual(empty_tables[0], 'table2')
        self.assertEqual(len(partially_populated_tables), 1)
        self.assertEqual(partially_populated_tables['table3'], 3)
    
    def test_query_error(self):
        """Test when a query fails"""
        # Mock database connector
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = [
            [{'count': 10}],  # table1
            None,             # table2 (query failed)
            [{'count': 5}]    # table3
        ]
        
        # Test tables
        tables = ['table1', 'table2', 'table3']
        
        # Run verification
        success, empty_tables, partially_populated_tables = verify_table_population(
            mock_db, tables, min_records=5
        )
        
        # Assertions
        self.assertFalse(success)
        self.assertEqual(len(empty_tables), 1)
        self.assertEqual(empty_tables[0], 'table2')
        self.assertEqual(len(partially_populated_tables), 0)

if __name__ == '__main__':
    unittest.main()
