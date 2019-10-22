<?php
/**
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; under version 2
 * of the License (non-upgradable).
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 *
 * Copyright (c) 2013-2015 (original work) Open Assessment Technologies SA (under the project TAO-PRODUCT);
 *
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 * @license GPLv2
 *
 */

namespace qtism\data\state;

use qtism\data\QtiComponent;
use qtism\data\QtiComponentCollection;
use qtism\common\collections\IdentifierCollection;

/**
 * The ShufflingGroup class.
 * 
 * A ShufflingGroup contains identifiers involved in shuffled interactions.
 * 
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 *
 */
class ShufflingGroup extends QtiComponent
{
    /**
     * A collection of identifiers.
     * 
     * @var \qtism\common\collections\IdentifierCollection
     * @qtism-bean-property
     */
    private $identifiers;
    
    /**
     * A collection of identifiers
     * 
     * @var \qtism\common\collections\IdentifierCollection
     * @qtism-bean-property
     */
    private $fixedIdentifiers;
    
    /**
     * Create a ShufflingGroup object.
     * 
     * @param \qtism\common\collections\IdentifierCollection $identifiers
     */
    public function __construct(IdentifierCollection $identifiers)
    {
        $this->setIdentifiers($identifiers);
        $this->setFixedIdentifiers(new IdentifierCollection());
    }
    
    /**
     * Set the identifiers involded in shuffled interactions.
     * 
     * @param \qtism\common\collections\IdentifierCollection $identifiers
     */
    public function setIdentifiers(IdentifierCollection $identifiers)
    {
        $this->identifiers = $identifiers;
    }
    
    /**
     * Get the identifiers involved in shuffled interactions.
     * 
     * @return \qtism\common\collections\IdentifierCollection
     */
    public function getIdentifiers()
    {
        return $this->identifiers;
    }
    
    /**
     * Set the identifiers involved in shuffled interactions that are fixed.
     * 
     * @param \qtism\common\collections\IdentifierCollection $fixedIdentifiers
     */
    public function setFixedIdentifiers(IdentifierCollection $fixedIdentifiers)
    {
        $this->fixedIdentifiers = $fixedIdentifiers;
    }
    
    /**
     * Get the identifiers involved in shuffled interactions that are fixed.
     * 
     * @return \qtism\common\collections\IdentifierCollection
     */
    public function getFixedIdentifiers()
    {
        return $this->fixedIdentifiers;
    }
    
    /**
     * Clone the ShufflingGroup object.
     */
    public function __clone()
    {
        $this->identifiers = clone $this->identifiers;
    }
    
    /**
     * @see \qtism\data\QtiComponent::getQtiClassName()
     */
    public function getQtiClassName()
    {
        return 'shufflingGroup';
    }
    
    /**
     * @see \qtism\data\QtiComponent::getComponents()
     */
    public function getComponents()
    {
        return new QtiComponentCollection();
    }
}
