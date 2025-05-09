"""
Report generation module for KOL analysis.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import json

from ..config.config import (
    TIME_INTERVALS,
    HIGH_IMPACT_THRESHOLDS,
    VOLUME_SPIKE_THRESHOLD,
    RESULTS_PATH
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, results_path: Path):
        """Initialize the report generator with analysis results."""
        try:
            self.df = pd.read_csv(results_path)
            if not self.df.empty:
                self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        except pd.errors.EmptyDataError:
            logger.warning("No data found in results file")
            self.df = pd.DataFrame()
    
    def identify_high_impact_tweets(self) -> pd.DataFrame:
        """Identify tweets that had significant price impact."""
        if self.df.empty:
            return pd.DataFrame()
            
        high_impact = []
        for _, row in self.df.iterrows():
            is_high_impact = False
            
            # Check price changes at different intervals
            if (abs(row['price_change_1h']) >= HIGH_IMPACT_THRESHOLDS['1h'] or
                abs(row['price_change_6h']) >= HIGH_IMPACT_THRESHOLDS['6h'] or
                abs(row['price_change_24h']) >= HIGH_IMPACT_THRESHOLDS['24h']):
                is_high_impact = True
            
            # Check volume spikes
            if row['volume_spike']:
                is_high_impact = True
            
            if is_high_impact:
                high_impact.append(row)
        
        return pd.DataFrame(high_impact)
    
    def generate_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics from the analysis results."""
        if self.df.empty:
            return {
                'total_tweets': 0,
                'unique_tokens': 0,
                'unique_kols': 0,
                'high_impact_tweets': 0,
                'avg_price_changes': {},
                'max_price_changes': {},
                'volume_stats': {},
                'market_data': {}
            }
        
        # Convert timestamp to datetime
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        
        # Basic stats
        stats = {
            'total_tweets': int(len(self.df)),
            'unique_tokens': int(self.df['token'].nunique()),
            'unique_kols': int(self.df['handle'].nunique()),
            'high_impact_tweets': int(len(self.identify_high_impact_tweets())),
            'avg_price_changes': {},
            'max_price_changes': {},
            'volume_stats': {},
            'market_data': {}
        }
        
        # Price change stats
        for interval in TIME_INTERVALS.keys():
            price_col = f'price_change_{interval}'
            if price_col in self.df.columns:
                stats['avg_price_changes'][interval] = float(self.df[price_col].mean())
                stats['max_price_changes'][interval] = float(self.df[price_col].max())
        
        # Volume stats
        if 'volume' in self.df.columns:
            stats['volume_stats'] = {
                'total_volume': float(self.df['volume'].sum()),
                'avg_volume': float(self.df['volume'].mean()),
                'max_volume': float(self.df['volume'].max())
            }
        
        # Market data stats
        if 'liquidity' in self.df.columns:
            stats['market_data'] = {
                'total_liquidity': float(self.df['liquidity'].sum()),
                'avg_liquidity': float(self.df['liquidity'].mean()),
                'max_liquidity': float(self.df['liquidity'].max())
            }
        
        return stats
    
    def plot_price_impact(self, token: str, save_path: Optional[Path] = None):
        """Generate price impact visualization for a specific token."""
        if self.df.empty:
            return
            
        token_data = self.df[self.df['token'] == token]
        if token_data.empty:
            return
            
        plt.figure(figsize=(12, 6))
        
        # Plot price changes for different intervals
        intervals = ['1h', '6h', '24h']
        changes = [token_data[f'price_change_{interval}'].mean() for interval in intervals]
        
        plt.bar(intervals, changes)
        plt.title(f'Price Impact Analysis for {token}')
        plt.xlabel('Time Interval')
        plt.ylabel('Price Change (%)')
        plt.xticks(rotation=45)
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
        else:
            plt.show()
    
    def generate_report(self, output_dir: Path):
        """Generate a comprehensive analysis report."""
        if self.df.empty:
            logger.warning("No data available for report generation")
            return
            
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate summary statistics
        stats = self.generate_summary_stats()
        with open(output_dir / 'summary_stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Identify high-impact tweets
        high_impact = self.identify_high_impact_tweets()
        high_impact.to_csv(output_dir / 'high_impact_tweets.csv', index=False)
        
        # Generate plots for each token
        for token in self.df['token'].unique():
            self.plot_price_impact(token, output_dir / f'{token}_impact.png')
        
        # Generate markdown report
        self._generate_markdown_report(output_dir / 'analysis_report.md', stats, high_impact)
    
    def _generate_markdown_report(self, output_path: Path, stats: Dict, high_impact: pd.DataFrame):
        """Generate a markdown report with analysis results."""
        with open(output_path, 'w') as f:
            f.write('# KOL Impact Analysis Report\n\n')
            
            # Summary Statistics
            f.write('## Summary Statistics\n\n')
            f.write(f'- Total Tweets Analyzed: {stats["total_tweets"]}\n')
            f.write(f'- Unique Tokens Mentioned: {stats["unique_tokens"]}\n')
            f.write(f'- Unique KOLs Analyzed: {stats["unique_kols"]}\n')
            f.write(f'- High-Impact Tweets: {stats["high_impact_tweets"]}\n\n')
            
            # Average Price Changes
            f.write('### Average Price Changes\n\n')
            for interval, change in stats['avg_price_changes'].items():
                f.write(f'- {interval}: {change:.2f}%\n')
            f.write('\n')
            
            # Maximum Price Changes
            f.write('### Maximum Price Changes\n\n')
            for interval, change in stats['max_price_changes'].items():
                f.write(f'- {interval}: {change:.2f}%\n')
            f.write('\n')
            
            # Volume Statistics
            f.write('### Volume Statistics\n\n')
            for interval, volume in stats['volume_stats'].items():
                f.write(f'- {interval}: {volume}\n')
            f.write('\n')
            
            # Market Statistics
            f.write('### Market Statistics\n\n')
            for interval, liquidity in stats['market_data'].items():
                f.write(f'- {interval} Liquidity: ${liquidity:.2f}\n')
            f.write('\n')
            
            # High-Impact Tweets
            f.write('## High-Impact Tweets\n\n')
            if not high_impact.empty:
                for _, tweet in high_impact.iterrows():
                    f.write(f'### Tweet from @{tweet["handle"]}\n\n')
                    f.write(f'- Token: {tweet["token"]} ({tweet["name"]})\n')
                    f.write(f'- Chain: {tweet["chain_id"]}\n')
                    f.write(f'- DEX: {tweet["dex_id"]}\n')
                    f.write(f'- Time: {tweet["timestamp"]}\n')
                    f.write(f'- Text: {tweet["text"]}\n')
                    f.write('\nPrice Changes:\n')
                    f.write(f'- 1h: {tweet["price_change_1h"]:.2f}%\n')
                    f.write(f'- 6h: {tweet["price_change_6h"]:.2f}%\n')
                    f.write(f'- 24h: {tweet["price_change_24h"]:.2f}%\n')
                    f.write('\nMarket Data:\n')
                    f.write(f'- Current Price: ${tweet["base_price"]:.8f}\n')
                    f.write(f'- Liquidity: ${tweet["liquidity"]:,.2f}\n')
                    f.write(f'- Market Cap: ${tweet["market_cap"]:,.2f}\n')
                    f.write(f'- 24h Volume: ${tweet["volume_24h"]:,.2f}\n')
                    f.write(f'- 24h Transactions: {tweet["txns_24h_buys"]} buys, {tweet["txns_24h_sells"]} sells\n')
                    f.write(f'- Volume Spike: {"Yes" if tweet["volume_spike"] else "No"}\n\n')
            else:
                f.write('No high-impact tweets found.\n')

def main():
    """Example usage of the ReportGenerator class."""
    # Example results file path
    results_path = Path('kol_analysis/data/results.csv')
    
    # Create report generator
    generator = ReportGenerator(results_path)
    
    # Generate report
    output_dir = Path('kol_analysis/reports')
    generator.generate_report(output_dir)
    
    # Print summary stats
    stats = generator.generate_summary_stats()
    print("\nSummary Statistics:")
    print(f"Total Tweets Analyzed: {stats['total_tweets']}")
    print(f"Unique Tokens: {stats['unique_tokens']}")
    print(f"High Impact Tweets: {stats['high_impact_tweets']}")

if __name__ == "__main__":
    main() 