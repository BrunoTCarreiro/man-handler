"""
Test script to see the before/after of chunk cleaning.

This shows you examples of raw chunks vs. cleaned chunks from your manual.
"""

from backend.ingest_enhanced import clean_chunk_with_llm
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def test_chunk_cleaning():
    """Load a manual, chunk it, and show before/after cleaning examples."""
    
    # Load the LG oven manual
    pdf_path = "data/manuals/wsed7613s_wsed7613b_wsed7612s_wsed7612b/d814e17fdd75346eb28064f68ada7b17828e151ec076124ea4272726a131d0c4.pdf"
    
    print("Loading manual...")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    print(f"Loaded {len(docs)} pages")
    
    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
    )
    chunks = splitter.split_documents(docs)
    
    print(f"Split into {len(chunks)} chunks\n")
    print("="*80)
    
    # Show 3 example chunks: before and after
    for i, example_idx in enumerate([10, 25, 50], 1):
        if example_idx >= len(chunks):
            continue
            
        chunk = chunks[example_idx]
        original_text = chunk.page_content
        
        print(f"\n{'='*80}")
        print(f"EXAMPLE {i} - Chunk #{example_idx}")
        print(f"{'='*80}")
        
        print(f"\n📄 ORIGINAL TEXT ({len(original_text)} chars):")
        print("-" * 80)
        print(original_text)
        print("-" * 80)
        
        print(f"\n🧹 Cleaning with LLM...")
        cleaned_text = clean_chunk_with_llm(original_text)
        
        print(f"\n✨ CLEANED TEXT ({len(cleaned_text)} chars):")
        print("-" * 80)
        print(cleaned_text)
        print("-" * 80)
        
        if not cleaned_text:
            print("\n💡 This chunk had no meaningful content and would be skipped!")
        else:
            reduction = 100 * (1 - len(cleaned_text) / len(original_text))
            print(f"\n📊 Size reduction: {reduction:.1f}%")
        
        print(f"\n{'='*80}\n")
        
        # Pause between examples
        if i < 3:
            input("Press Enter to see next example...")
    
    print("\n" + "="*80)
    print("Test complete!")
    print("="*80)
    print("\nTo rebuild your vector store with cleaned chunks:")
    print("  python -m backend.ingest_enhanced")
    print("\nThis will take ~10-20 minutes but will significantly improve")
    print("retrieval quality by removing noise and normalizing content.")


if __name__ == "__main__":
    test_chunk_cleaning()



