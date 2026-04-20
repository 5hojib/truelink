#!/usr/bin/env python3
"""Test script for TrueLink changes."""

import sys

# Force reload
for key in list(sys.modules.keys()):
    if 'truelink' in key:
        del sys.modules[key]

from truelink import TrueLinkResolver

def test_cache():
    """Test cache functionality."""
    print("=" * 50)
    print("Testing Cache Management")
    print("=" * 50)

    resolver = TrueLinkResolver(cache_max_size=10, cache_ttl=60)

    # Test cache type
    print(f"\n1. Cache type: {type(resolver._cache).__name__}")
    print(f"   Expected: _LRUCache")

    # Test cache attributes
    print(f"\n2. Cache attributes:")
    print(f"   - Has max_size: {hasattr(resolver._cache, 'max_size')}")
    print(f"   - Has ttl: {hasattr(resolver._cache, 'ttl')}")
    print(f"   - Has get method: {hasattr(resolver._cache, 'get')}")
    print(f"   - Has set method: {hasattr(resolver._cache, 'set')}")
    print(f"   - Has clear method: {hasattr(resolver._cache, 'clear')}")
    print(f"   - Has cleanup_expired method: {hasattr(resolver._cache, 'cleanup_expired')}")

    if hasattr(resolver._cache, 'max_size'):
        print(f"\n3. Cache configuration:")
        print(f"   - max_size: {resolver._cache.max_size}")
        print(f"   - ttl: {resolver._cache.ttl}")

    # Test cache methods
    print(f"\n4. Testing cache methods:")
    TrueLinkResolver.clear_cache()
    print("   - clear_cache() executed successfully")

    removed = TrueLinkResolver.cleanup_cache()
    print(f"   - cleanup_cache() executed, removed {removed} entries")

def test_session_cleanup():
    """Test session cleanup functionality."""
    print("\n" + "=" * 50)
    print("Testing Session Cleanup")
    print("=" * 50)

    print(f"\n1. Testing cleanup_resolver_instances():")
    TrueLinkResolver.cleanup_resolver_instances()
    print("   - cleanup_resolver_instances() executed successfully")

def test_base_methods():
    """Test BaseResolver methods."""
    print("\n" + "=" * 50)
    print("Testing BaseResolver Methods")
    print("=" * 50)

    from truelink.resolvers.base import BaseResolver

    print(f"\n1. BaseResolver has _raise_extraction_failed: {hasattr(BaseResolver, '_raise_extraction_failed')}")
    print(f"2. BaseResolver has _raise_invalid_url: {hasattr(BaseResolver, '_raise_invalid_url')}")

def test_other_methods():
    """Test other new methods."""
    print("\n" + "=" * 50)
    print("Testing Other Methods")
    print("=" * 50)

    print(f"\n1. Testing is_supported():")
    result = TrueLinkResolver.is_supported("https://buzzheavier.com/test")
    print(f"   - buzzheavier.com: {result}")

    result = TrueLinkResolver.is_supported("https://unknown.com/test")
    print(f"   - unknown.com: {result}")

    print(f"\n2. Testing get_supported_domains():")
    domains = TrueLinkResolver.get_supported_domains()
    print(f"   - Found {len(domains)} supported domains")

if __name__ == "__main__":
    try:
        test_cache()
        test_session_cleanup()
        test_base_methods()
        test_other_methods()

        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("=" * 50)
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
