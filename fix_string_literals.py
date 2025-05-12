if fixed_content != content:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(fixed_content)
                logger.info(f"Fixed string literals in {filename}")
                results[filename] = True
            else:
                logger.info(f"No string literal issues found in {filename}")
                results[filename] = False

        except Exception as e:
            logger.error(f"Error fixing string literals in {filename}: {str(e)}")
            results[filename] = False

    return results

def main():
    """Main function to run the script."""
    logger.info("Starting string literal fix script...")

    # Get files from command line args or use default
    files = sys.argv[1:] if len(sys.argv) > 1 else None

    # Fix string literals
    results = fix_string_literals(files)

    # Count successes
    successes = sum(1 for result in results.values() if result)
    logger.info(f"Fixed {successes} out of {len(results)} files")

    return 0 if successes > 0 or len(results) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())