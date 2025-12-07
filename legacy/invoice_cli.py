#!/usr/bin/env python3
"""
Invoice Processing CLI
Simple command-line interface for processing PDF invoices and generating accounting reports.

Quick Start:
    # Process specific PDF files
    python invoice_cli.py invoice1.pdf invoice2.pdf invoice3.pdf
    
    # Process all PDFs in a folder
    python invoice_cli.py --folder data/
    
    # Custom output location
    python invoice_cli.py invoice1.pdf --output reports/
"""
import sys
import argparse
from pathlib import Path
from invoice_workflow import process_invoices_to_csvs


def main():
    parser = argparse.ArgumentParser(
        description='Process PDF invoices and generate accounting reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process specific PDF files
  python invoice_cli.py invoice1.pdf invoice2.pdf invoice3.pdf
  
  # Process PDFs and save to custom output folder
  python invoice_cli.py invoice1.pdf invoice2.pdf --output reports/
  
  # Process all PDFs in a folder
  python invoice_cli.py --folder data/ --output reports/
  
  # Process all PDFs in current directory
  python invoice_cli.py --folder .
        """
    )
    
    parser.add_argument(
        'pdfs',
        nargs='*',
        help='PDF invoice files to process'
    )
    
    parser.add_argument(
        '--folder', '-f',
        type=str,
        help='Folder containing PDF invoices to process'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output',
        help='Output folder for generated CSV files (default: output)'
    )
    
    args = parser.parse_args()
    
    # Determine input files
    pdf_files = []
    
    if args.folder:
        # Process all PDFs in folder
        folder_path = Path(args.folder)
        if not folder_path.exists():
            print(f"Error: Folder '{args.folder}' does not exist")
            sys.exit(1)
        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in '{args.folder}'")
            sys.exit(1)
        print(f"Found {len(pdf_files)} PDF file(s) in '{args.folder}'")
    elif args.pdfs:
        # Process specified PDF files
        pdf_files = [Path(pdf) for pdf in args.pdfs]
        # Verify files exist
        missing_files = [f for f in pdf_files if not f.exists()]
        if missing_files:
            print(f"Error: The following files do not exist:")
            for f in missing_files:
                print(f"  - {f}")
            sys.exit(1)
    else:
        parser.print_help()
        print("\nError: Please provide either PDF files or use --folder option")
        sys.exit(1)
    
    # Create temporary input folder if processing specific files
    if args.pdfs and not args.folder:
        import tempfile
        import shutil
        
        # Create temporary folder
        temp_input = Path(tempfile.mkdtemp(prefix="invoice_processing_"))
        try:
            # Copy PDFs to temp folder
            print(f"\nProcessing {len(pdf_files)} invoice(s)...")
            for pdf_file in pdf_files:
                shutil.copy2(pdf_file, temp_input / pdf_file.name)
                print(f"  - {pdf_file.name}")
            
            # Process invoices
            process_invoices_to_csvs(str(temp_input), args.output)
            
        finally:
            # Clean up temp folder
            shutil.rmtree(temp_input, ignore_errors=True)
    else:
        # Process from folder
        print(f"\nProcessing invoices from '{args.folder}'...")
        process_invoices_to_csvs(args.folder, args.output)
    
    print(f"\nProcessing complete! CSV files saved to: {args.output}/")


if __name__ == "__main__":
    main()

